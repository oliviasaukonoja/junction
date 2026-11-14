from .cli import main

if __name__ == "__main__":     # guard required: process-pool workers re-import the main module
    raise SystemExit(main())
