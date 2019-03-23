import mosek
import time


if __name__ == "__main__":
    with open('/Users/leot/Desktop/its-on-like-XXXX.jpg', 'rb') as f:
        x = str(f.read())

    print(x.find('afnom'))
    print(x[182727:182740])
    print(x)


