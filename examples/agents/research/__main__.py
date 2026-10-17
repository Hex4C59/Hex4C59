if __package__:
    from .app import main
else:
    from app import main

raise SystemExit(main())
