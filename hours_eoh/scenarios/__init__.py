"""
scenarios/ — Applied research: stress tests, shock scenarios, and sweep tools.

Each sub-module is a self-contained scenario runner built on top of core/.
Canonical imports::

    from hours_eoh.scenarios.sweep import epsilon_sweep
    from hours_eoh.scenarios.shocks import (
        automation_failure_shock, demographic_shock, ecological_eoh_spike,
        labor_income_shock, compound_shock,
    )
    from hours_eoh.scenarios.maintenance import deferred_maintenance_crisis, care_registration_delay
    from hours_eoh.scenarios.recovery import maintenance_recovery_schedule
    from hours_eoh.scenarios.sensitivity import fiscal_parameter_sweep
    from hours_eoh.scenarios.long_run import (
        canonical_arc_trajectory, trust_depletion_stress, automation_transition_trajectory,
    )
    from hours_eoh.scenarios.indust_overshoot import (
        indust_overshoot_baseline, indust_recovery_trajectory,
    )
    from hours_eoh.scenarios.guf_stress import (
        guf_fiscal_integration, guf_writedown_scenario, guf_revenue_sweep,
        automation_levy_guf_stress,
    )

None of these modules are imported by core/ — the dependency is one-way.
"""
