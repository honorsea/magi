import numpy as np
import scipy.stats as st
from typing import Dict, Any

from magi.physical.constants import (
    CW_TIMING_PARAMS, MW_TIMING_PARAMS, CW_PHASE_TO_TIMING, 
    ROBOT_PHASES, PHYSIO_HR_BASELINES, PHYSIO_IBI_BASELINES
)
from magi.digital.config import ConfigState
from magi.digital.models import PhysioRecord

#  SECTION 4 — TASK DURATION SAMPLER
#              Draws phase durations from fitted empirical distributions.
# ─────────────────────────────────────────────────────────────────────────────

class TaskDurationSampler:
    """
    Generates stochastic task durations from the empirically-fitted
    probability distributions identified in 1_data_preprocessing.py.

    The sampler wraps scipy.stats distributions and applies the
    robot_speed_factor from ConfigState to all robot-controlled phases.

    Design principle: deterministic robot phases receive no randomness
    (CV ≈ 0 confirmed in preprocessing). Human phases retain their
    fitted variability. All samples are clipped to a minimum of 0.5s
    to prevent non-physical zero-duration events.

    Parameters
    ----------
    config : ConfigState
        Live configuration reference (sampler reads speed factor at call time).
    rng : np.random.Generator
        Seeded NumPy Generator for reproducible replication runs.
    """

    _MIN_DURATION: float = 0.5  # seconds — physical lower bound

    def __init__(self, config: ConfigState, rng: np.random.Generator):
        self.config = config
        self.rng    = rng

    def sample_cw_phase(self, phase_label: str) -> float:
        """
        Draw a duration for one CW task phase.

        Args:
            phase_label: One of the CW_TASK_SEQUENCE labels.

        Returns:
            Duration in seconds (≥ _MIN_DURATION).
        """
        timing_key = CW_PHASE_TO_TIMING[phase_label]
        params     = CW_TIMING_PARAMS[timing_key]
        dist_name  = params["distribution"]

        duration = self._draw(dist_name, params)

        # Apply robot speed factor to robot-controlled phases only.
        # Faster robot → shorter robot phase duration → tighter HRC cycle.
        if phase_label in ROBOT_PHASES:
            duration /= self.config.robot_speed_factor

        return max(duration, self._MIN_DURATION)

    def sample_mw_duration(self) -> float:
        """
        Draw a total duration for the Manual Workstation cycle.

        The MW aggregate encompasses 06_filter_assembly + 07_bag_leave.
        The robot speed factor does NOT apply here (pure human work).

        Returns:
            Duration in seconds (≥ _MIN_DURATION).
        """
        params    = MW_TIMING_PARAMS["Manual_Task_Duration"]
        dist_name = params["distribution"]
        return max(self._draw(dist_name, params), self._MIN_DURATION)

    def sample_arrival_interval(self) -> float:
        """
        Draw a product inter-arrival time from the takt time distribution.

        Models slight conveyor pacing variability around the target takt.
        If jitter CV = 0, arrivals are perfectly deterministic.

        Returns:
            Inter-arrival interval in seconds.
        """
        takt = self.config.takt_time_seconds
        cv   = self.config.inter_arrival_jitter_cv
        if cv <= 0:
            return takt
        std = takt * cv
        interval = self.rng.normal(loc=takt, scale=std)
        return max(interval, 1.0)  # at least 1 second between products

    # ------------------------------------------------------------------
    # Private dispatch: map distribution name → scipy sample
    # ------------------------------------------------------------------

    def _draw(self, dist_name: str, params: Dict) -> float:
        """Internal: draw one sample from the specified distribution."""
        if dist_name == "constant":
            return params["mean"]

        elif dist_name == "norm":
            return float(self.rng.normal(loc=params["mean"],
                                         scale=params["std_dev"]))

        elif dist_name == "expon":
            # Shifted exponential: X = loc + Expon(scale)
            # loc represents the minimum feasible reaction time.
            return params["loc"] + float(self.rng.exponential(scale=params["scale"]))

        elif dist_name == "lognorm":
            # scipy lognorm(s, loc, scale): s = shape, scale = e^mu
            # Using numpy: X = loc + exp(Normal(mu, sigma))
            mu    = np.log(params["scale"])
            sigma = params["shape"]
            return params["loc"] + float(np.exp(self.rng.normal(loc=mu, scale=sigma)))

        elif dist_name == "gamma":
            return params["loc"] + float(self.rng.gamma(shape=params["shape"],
                                                         scale=params["scale"]))

        elif dist_name == "weibull_min":
            # scipy weibull_min(c, loc, scale)
            u = float(self.rng.uniform())
            return params["loc"] + params["scale"] * (-np.log(1 - u)) ** (1 / params["c"])

        elif dist_name == "uniform":
            return float(self.rng.uniform(low=params["loc"],
                                          high=params["loc"] + params["scale"]))
        else:
            raise ValueError(f"Unsupported distribution: '{dist_name}'")


# ─────────────────────────────────────────────────────────────────────────────
class PhysiologicalSampler:
    """
    Generates physiologically realistic observations for each simulated
    task-phase execution.

    The model has three additive components:

    1. **Empirical Baseline** — draws from the per-(worker, task) HR and
       IBI distributions measured in Dataset 2 (REPORT.txt Steps 6.11, 7.7).

    2. **Workload Delta** — applies a first-order linear correction when
       the Cognitive Layer changes configurable parameters (robot speed,
       takt time). Calibrated to the within-dataset CW/MW HR differential
       observed in REPORT.txt Step 6.4 (≈ +4–7 BPM MW over CW for workers
       with both stations). Coefficient derivation is documented inline.

    3. **Fatigue Overlay** — models within-shift HR drift using a square-
       root growth function (Åstrand & Rodahl, 1986), saturating at a
       physiologically plausible ceiling of 8 BPM above baseline.
       IBI increases with fatigue (longer inter-blink gaps) following the
       visual fatigue model of Galley & Andrés (2002).

    Parameters
    ----------
    config : ConfigState
        Live configuration for workload delta computation.
    rng    : np.random.Generator
        Seeded generator for reproducible sampling.
    """

    # Fatigue overlay ceiling (BPM) — physiological cap for moderate work
    _FATIGUE_HR_CAP:     float = 8.0
    # Fatigue growth coefficient (BPM / sqrt(minutes))
    # Calibrated: 8 BPM cap reached at ~400 minutes → k = 8/sqrt(400) = 0.4
    _FATIGUE_GROWTH_K:   float = 0.4
    # Fatigue IBI elongation (ms per minute of elapsed work)
    # Literature: ~0.3% IBI increase per 10 minutes of sustained visual work
    _FATIGUE_IBI_K:      float = 3.0

    # Workload response coefficients for human-active CW phases.
    # Faster robot → shorter human wait → higher sustained HR per cycle.
    # Value (0.15): calibrated to the observed +4–7 BPM CW→MW differential
    # across Workers 001 & 002 (the only workers with both CW and MW data).
    # This represents a ~2× increase in physical activity (CW wait → MW).
    _WL_COEF_HUMAN_ACTIVE: float = 0.15
    # Robot wait phases: less recovery time when robot is faster.
    _WL_COEF_ROBOT_WAIT:   float = 0.08
    # Takt pace response coefficient (HR per unit pace increase)
    _WL_COEF_TAKT:         float = 0.12
    # Reference takt (baseline configuration)
    _REFERENCE_TAKT:       float = 60.0

    def __init__(self, config: ConfigState, rng: np.random.Generator):
        self.config = config
        self.rng    = rng

    def sample(
        self,
        worker_id:       str,
        workstation:     str,
        task_label:      str,
        sim_time:        float,
        elapsed_minutes: float,
        phase_duration:  float,
        product_id:      int,
    ) -> PhysioRecord:
        """
        Produce one PhysioRecord for a completed task phase.

        Args:
            worker_id:       Worker performing this phase.
            workstation:     "CW" or "MW".
            task_label:      Task label (e.g. "01_pick_fix1").
            sim_time:        Current simulation clock (seconds).
            elapsed_minutes: How long this worker has been active this shift.
            phase_duration:  Sampled task duration (seconds).
            product_id:      Unit currently in process.

        Returns:
            PhysioRecord populated with all three HR components.
        """
        # ── Component 1: Empirical Baseline ───────────────────────────
        hr_mean, hr_std, rr_mean = PHYSIO_HR_BASELINES[worker_id][task_label]
        # Add within-task HR variability (Normal noise around task-level mean)
        hr_noise   = float(self.rng.normal(loc=0.0, scale=hr_std * 0.3))
        hr_baseline = hr_mean + hr_noise

        ibi_mean, ibi_std = PHYSIO_IBI_BASELINES[worker_id][task_label]
        ibi_noise    = float(self.rng.normal(loc=0.0, scale=ibi_std * 0.3))
        ibi_baseline = max(ibi_mean + ibi_noise, 100.0)  # floor at 100ms

        # ── Component 2: Workload Delta (configuration response) ───────
        hr_delta = self._workload_delta(task_label, hr_mean)

        # ── Component 3: Fatigue Overlay (within-shift drift) ─────────
        hr_fatigue  = self._fatigue_hr_overlay(elapsed_minutes,
                                               workload_intensity=self._workload_intensity())
        ibi_fatigue = self._fatigue_ibi_overlay(ibi_baseline, elapsed_minutes)

        # ── Composite physiological signal ────────────────────────────
        hr_final  = max(hr_baseline + hr_delta + hr_fatigue, 40.0)
        hr_final  = min(hr_final, 200.0)   # physiological ceiling
        ibi_final = max(ibi_baseline + ibi_fatigue, 100.0)

        rr_final  = 60_000.0 / hr_final   # RR interval from HR (ms)

        # Normalised fatigue score [0, 1]
        fatigue_score = min(hr_fatigue / self._FATIGUE_HR_CAP, 1.0)

        return PhysioRecord(
            sim_time=sim_time,
            elapsed_minutes=elapsed_minutes,
            worker_id=worker_id,
            workstation=workstation,
            task_label=task_label,
            hr_bpm=round(hr_final, 2),
            rr_interval_ms=round(rr_final, 1),
            ibi_ms=round(ibi_final, 1),
            hr_baseline=round(hr_baseline, 2),
            hr_delta=round(hr_delta, 3),
            hr_fatigue=round(hr_fatigue, 3),
            fatigue_score=round(fatigue_score, 4),
            phase_duration=round(phase_duration, 3),
            product_id=product_id,
        )

    # ------------------------------------------------------------------
    # Workload Delta Model
    # ------------------------------------------------------------------

    def _workload_delta(self, task_label: str, baseline_hr: float) -> float:
        """
        First-order linear workload correction based on active configuration.

        When robot_speed_factor > 1 (faster robot):
          - Human-active phases: cycle density increases → sustained HR rises.
          - Robot-wait phases: recovery window shrinks → HR stays elevated.
        When takt_time < reference:
          - Pace increase → higher metabolic demand for MW operator.

        Coefficients calibrated to within-dataset CW/MW differential
        (REPORT.txt Step 6.4): Workers 001 & 002 show +4.4 and +7.2 BPM
        MW over CW respectively, representing the ergonomic cost of the
        continuous manual station versus the HRC collaboration pattern.
        """
        spf = self.config.robot_speed_factor - 1.0  # 0 at baseline

        if task_label in {"01_pick_fix1", "03_pick_fix2", "05_pick_leave"}:
            # Human-active phases: faster robot → denser cycle → elevated HR
            delta = baseline_hr * spf * self._WL_COEF_HUMAN_ACTIVE
        elif task_label in {"02_visual_check", "04_grounding_test"}:
            # Robot-wait phases: shorter rest window → less recovery
            delta = baseline_hr * spf * self._WL_COEF_ROBOT_WAIT
        else:
            # MW phases: affected by takt pace, not robot speed
            pace_delta = (self._REFERENCE_TAKT / self.config.takt_time_seconds) - 1.0
            delta = baseline_hr * pace_delta * self._WL_COEF_TAKT

        return delta

    def _workload_intensity(self) -> float:
        """
        Scalar workload intensity [0.5, 2.0] combining speed and pace factors.
        Used to modulate the fatigue growth rate.
        """
        speed_intensity = self.config.robot_speed_factor
        pace_intensity  = self._REFERENCE_TAKT / self.config.takt_time_seconds
        return min(speed_intensity * pace_intensity, 2.0)

    # ------------------------------------------------------------------
    # Fatigue Overlay Model
    # ------------------------------------------------------------------

    def _fatigue_hr_overlay(self, elapsed_minutes: float,
                             workload_intensity: float) -> float:
        """
        HR fatigue drift: square-root growth, saturating at _FATIGUE_HR_CAP.

        Mathematical form:
            ΔHR_fatigue(t) = k · √t · intensity,  capped at 8 BPM

        Reference: Åstrand & Rodahl (1986), Textbook of Work Physiology,
        Ch. 15 — HR response to sustained moderate-intensity work.

        Args:
            elapsed_minutes: Cumulative worked time (minutes).
            workload_intensity: Scalar intensity modifier.

        Returns:
            HR elevation (BPM) attributable to fatigue.
        """
        growth = self._FATIGUE_GROWTH_K * (elapsed_minutes ** 0.5) * workload_intensity
        return min(growth, self._FATIGUE_HR_CAP)

    def _fatigue_ibi_overlay(self, baseline_ibi_ms: float,
                              elapsed_minutes: float) -> float:
        """
        IBI fatigue elongation: linear growth modelling visual fatigue.

        As cognitive and visual fatigue accumulate, blink frequency decreases
        (IBI increases). This is distinct from the high-workload blink
        suppression effect, which acts in the opposite direction.

        Reference: Galley & Andrés (2002), Ergonomics — IBI as fatigue
        indicator in sustained visual tasks.

        Note: In prolonged sessions, both suppression (task-induced) and
        elongation (fatigue-induced) can co-occur. The overlay here models
        the background fatigue drift; the empirical baseline already captures
        task-level suppression from Dataset 2.

        Args:
            baseline_ibi_ms: Empirical IBI for this (worker, task) cell.
            elapsed_minutes: Cumulative worked time.

        Returns:
            IBI increment (ms) due to fatigue accumulation.
        """
        return self._FATIGUE_IBI_K * elapsed_minutes


# ─────────────────────────────────────────────────────────────────────────────
