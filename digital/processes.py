import simpy
from typing import Callable, Dict, List, Any, Optional

from magi.physical.constants import CW_TASK_SEQUENCE, MW_TASK_SEQUENCE, ROBOT_PHASES
from magi.physical.samplers import TaskDurationSampler, PhysiologicalSampler
from magi.digital.config import ConfigState
from magi.digital.models import TaskRecord, PhysioRecord

#  SECTION 7 — SIMPY PROCESS DEFINITIONS
#              Models the Silverline assembly line as concurrent SimPy processes.
# ─────────────────────────────────────────────────────────────────────────────

def _arrival_process(
    env:       simpy.Environment,
    buffer:    simpy.Store,
    sampler:   TaskDurationSampler,
    config:    ConfigState,
    counters:  Dict,
) -> None:
    """
    SimPy generator: product arrival into the assembly line.

    Products arrive at the head of the line according to the configured takt
    time with optional jitter (inter_arrival_jitter_cv). Each product is
    represented as an integer ID pushed into `buffer` (the CW input store).

    In the real Silverline line, products arrive from an upstream conveyor.
    The takt time represents the Lean-derived target rate: slower takt = less
    pressure; faster takt = higher throughput demand (and physiological load).

    Args:
        env:      SimPy environment.
        buffer:   Finite-capacity SimPy Store representing the CW input queue.
        sampler:  TaskDurationSampler for inter-arrival intervals.
        config:   Live configuration (takt time read at each arrival).
        counters: Shared mutable dict for tracking generated product count.
    """
    product_id = 0
    while True:
        interval = sampler.sample_arrival_interval()
        yield env.timeout(interval)
        product_id += 1
        counters["generated"] += 1
        # Push product into the CW buffer (blocks if buffer is full → backpressure)
        if len(buffer.items) < config.buffer_capacity:
            buffer.put(product_id)
        # If buffer is full, unit is lost (models conveyor overflow / rework)
        else:
            counters["dropped"] += 1


def _cw_process(
    env:          simpy.Environment,
    buffer:       simpy.Store,
    mw_buffer:    simpy.Store,
    robot:        simpy.Resource,
    config:       ConfigState,
    dur_sampler:  TaskDurationSampler,
    phy_sampler:  PhysiologicalSampler,
    task_log:     List,
    physio_log:   List,
    cw_busy_time: List[float],
    robot_busy:   List[float],
    event_sink:   Optional[Callable[[str, Dict[str, Any]], None]] = None,
) -> None:
    """
    SimPy generator: Collaborative Workstation (CW) worker process.

    The CW worker continuously cycles through the five-phase HRC sequence:

    Phase 1 — 01_pick_fix1 (human)    : Worker picks and secures product.
    Phase 2 — 02_visual_check (robot) : Robot seizes robot resource and
                                         performs visual + barcode inspection.
    Phase 3 — 03_pick_fix2 (human)    : Worker reacts and repositions product.
    Phase 4 — 04_grounding_test (robot): Robot performs grounding test.
    Phase 5 — 05_pick_leave (human)   : Worker finalises and returns product.

    The robot resource models the shared robot arm: it cannot perform both
    robot actions simultaneously (capacity=1), which is architecturally
    correct — the same arm executes both robot phases sequentially within
    one product cycle.

    Physiological records are emitted for every phase (human or robot-wait),
    anchored to the CW worker's profile.

    Args:
        env, buffer, mw_buffer, robot: SimPy primitives.
        config: Live configuration.
        dur_sampler: Task duration sampler.
        phy_sampler: Physiological sampler.
        task_log, physio_log: Shared log lists (appended in-place).
        cw_busy_time: Mutable list accumulating CW worker busy time.
        robot_busy:   Mutable list accumulating robot busy time.
    """
    cw_elapsed_minutes = 0.0  # cumulative worked time for fatigue overlay

    while True:
        # ── Wait for a product to arrive in the CW input buffer ────────
        arrival_time = env.now
        product_id   = yield buffer.get()
        queue_wait   = env.now - arrival_time

        # ── Execute the five CW phases sequentially ────────────────────
        for phase_label in CW_TASK_SEQUENCE:
            phase_start = env.now
            is_robot    = phase_label in ROBOT_PHASES

            if is_robot:
                # Robot phases: seize the robot resource.
                with robot.request() as req:
                    yield req
                    robot_start = env.now
                    duration    = dur_sampler.sample_cw_phase(phase_label)
                    yield env.timeout(duration)
                    robot_busy.append(env.now - robot_start)
            else:
                duration = dur_sampler.sample_cw_phase(phase_label)
                yield env.timeout(duration)

            phase_end            = env.now
            actual_duration      = phase_end - phase_start
            cw_elapsed_minutes  += actual_duration / 60.0

            # Emit physiological record for every phase
            physio_rec = phy_sampler.sample(
                worker_id=config.cw_worker_id,
                workstation="CW",
                task_label=phase_label,
                sim_time=env.now,
                elapsed_minutes=cw_elapsed_minutes,
                phase_duration=actual_duration,
                product_id=product_id,
            )
            physio_log.append(physio_rec)

            # Log task record
            task_log.append(TaskRecord(
                product_id=product_id,
                workstation="CW",
                task_label=phase_label,
                worker_id=config.cw_worker_id,
                phase_start_time=phase_start,
                phase_end_time=phase_end,
                phase_duration=actual_duration,
                is_robot_phase=is_robot,
                queue_wait_time=queue_wait if phase_label == CW_TASK_SEQUENCE[0] else 0.0,
                physio=physio_rec,
            ))

            if event_sink is not None:
                tr = task_log[-1]
                event_sink("task_record", {
                    "product_id": tr.product_id, "workstation": tr.workstation,
                    "task_label": tr.task_label, "worker_id": tr.worker_id,
                    "phase_start": tr.phase_start_time, "phase_end": tr.phase_end_time,
                    "duration": tr.phase_duration, "is_robot": tr.is_robot_phase,
                    "queue_wait": tr.queue_wait_time,
                    "hr": physio_rec.hr_bpm, "ibi": physio_rec.ibi_ms,
                    "fatigue": physio_rec.fatigue_score,
                })

            cw_busy_time.append(actual_duration)

        # ── Pass completed product to MW buffer ─────────────────────────
        # MW buffer is also finite: models physical holding space.
        if len(mw_buffer.items) < config.buffer_capacity:
            mw_buffer.put(product_id)


def _mw_process(
    env:          simpy.Environment,
    mw_buffer:    simpy.Store,
    config:       ConfigState,
    dur_sampler:  TaskDurationSampler,
    phy_sampler:  PhysiologicalSampler,
    task_log:     List,
    physio_log:   List,
    mw_busy_time: List[float],
    event_sink:   Optional[Callable[[str, Dict[str, Any]], None]] = None,
) -> None:
    """
    SimPy generator: Manual Workstation (MW) worker process.

    The MW worker performs filter assembly, metallic label assembly, external
    cleaning, bagging, and final barcode verification as one aggregate cycle.
    The aggregate duration is drawn from the Normal distribution fitted to
    the combined 06_filter_assembly + 07_bag_leave durations.

    The MW physiological record is attached to "06_filter_assembly" as the
    primary task label (the longer sub-phase), with a separate record for
    "07_bag_leave" using a duration split proportional to the empirical
    task-level ECG record counts from REPORT.txt Step 6.3:
    06_filter_assembly: 4,448 ECG records; 07_bag_leave: 1,781 ECG records
    → split ratio ≈ 71.4% / 28.6%.

    Args:
        env, mw_buffer: SimPy primitives.
        config: Live configuration.
        dur_sampler: Task duration sampler.
        phy_sampler: Physiological sampler.
        task_log, physio_log: Shared log lists.
        mw_busy_time: Mutable list accumulating MW worker busy time.
    """
    mw_elapsed_minutes = 0.0
    _SPLIT_FA  = 0.714   # fraction allocated to 06_filter_assembly
    _SPLIT_BL  = 0.286   # fraction allocated to 07_bag_leave

    while True:
        arrival_time = env.now
        product_id   = yield mw_buffer.get()
        queue_wait   = env.now - arrival_time

        total_duration = dur_sampler.sample_mw_duration()
        dur_fa = total_duration * _SPLIT_FA
        dur_bl = total_duration * _SPLIT_BL

        for task_label, sub_duration in [
            ("06_filter_assembly", dur_fa),
            ("07_bag_leave",       dur_bl),
        ]:
            phase_start         = env.now
            yield env.timeout(sub_duration)
            phase_end           = env.now
            mw_elapsed_minutes += sub_duration / 60.0

            physio_rec = phy_sampler.sample(
                worker_id=config.mw_worker_id,
                workstation="MW",
                task_label=task_label,
                sim_time=env.now,
                elapsed_minutes=mw_elapsed_minutes,
                phase_duration=sub_duration,
                product_id=product_id,
            )
            physio_log.append(physio_rec)

            task_log.append(TaskRecord(
                product_id=product_id,
                workstation="MW",
                task_label=task_label,
                worker_id=config.mw_worker_id,
                phase_start_time=phase_start,
                phase_end_time=phase_end,
                phase_duration=sub_duration,
                is_robot_phase=False,
                queue_wait_time=queue_wait if task_label == "06_filter_assembly" else 0.0,
                physio=physio_rec,
            ))

            if event_sink is not None:
                tr = task_log[-1]
                event_sink("task_record", {
                    "product_id": tr.product_id, "workstation": tr.workstation,
                    "task_label": tr.task_label, "worker_id": tr.worker_id,
                    "phase_start": tr.phase_start_time, "phase_end": tr.phase_end_time,
                    "duration": tr.phase_duration, "is_robot": tr.is_robot_phase,
                    "hr": physio_rec.hr_bpm, "ibi": physio_rec.ibi_ms,
                    "fatigue": physio_rec.fatigue_score,
                })

            mw_busy_time.append(sub_duration)


# ─────────────────────────────────────────────────────────────────────────────
