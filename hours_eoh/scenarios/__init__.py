"""
scenarios/ — Applied research: stress tests, shock scenarios, and sweep tools.

Each sub-module is a self-contained scenario runner built on top of core/.
Canonical imports::

    from hours_eoh.scenarios.sweep import epsilon_sweep
    from hours_eoh.scenarios.shocks import automation_failure_shock, demographic_shock
    from hours_eoh.scenarios.maintenance import deferred_maintenance_crisis, care_registration_delay
    from hours_eoh.scenarios.recovery import maintenance_recovery_schedule
    from hours_eoh.scenarios.sensitivity import fiscal_parameter_sweep

None of these modules are imported by core/ — the dependency is one-way.
"""
