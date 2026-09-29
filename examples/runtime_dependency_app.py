from ctypes import CDLL

# Replace with a real runtime-loaded shared library available on the build host.
# Example: CDLL("/opt/vendor/lib/libexample.so")
#
# The important property is that the library is loaded at runtime rather than
# imported as a normal Python module.
def main():
    print("runtime dependency demo")


if __name__ == "__main__":
    main()
