"""
Core EOH → TEH pipeline primitives.

Direct submodule imports are the intended pattern::

    from hours_eoh.core.eoh_generation import total_eoh
    from hours_eoh.core.dashboard import system_dashboard
    from hours_eoh.core.fiscal import fiscal_snapshot

This package does not re-export; callers name the submodule explicitly
so import paths are always traceable.
"""
