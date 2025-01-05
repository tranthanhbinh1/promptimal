# Local
try:
    from promptimal import main
except ImportError:
    from . import main

if __name__ == "__main__":
    main()
