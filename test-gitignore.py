from tqdm import tqdm
from time import sleep
import numpy as np
import scipy.stats as st
import random


def test_expected_shortfall():
    mean = 1533.28
    std = 98.8480
    ddl = 1630.77
    cdf = st.norm(mean, std).cdf(ddl)
    ES = mean + std * st.norm.pdf(st.norm.ppf(cdf)) / (1 - cdf) - ddl if cdf < 1 else 0
    print(f'cdf:{cdf}, ES:{ES}')

    # s = np.random.normal(mean, std, 20000)
    # a = 0
    # b = 0
    # for ss in s:
    #     if ss > ddl:
    #         a += 1
    #         b += ss
    #
    # print(s)
    # print(b/a)


def test_monotonicity():
    for cdf in tqdm(range(1, 990)):
        cdf1 = cdf
        cdf2 = cdf + 1
        cdf1 /= 1000
        cdf2 /= 1000
        a = st.norm.pdf(st.norm.ppf(cdf1)) / (1 - cdf1)
        b = st.norm.pdf(st.norm.ppf(cdf2)) / (1 - cdf2)
        if not b > a:
            print([cdf1, a], [cdf2, b])
        assert b > a


def test_monotonicity2():
    n = 0
    n1 = 0
    while True:
        mean1 = random.randint(500, 700)
        std1 = random.randint(50, 200)
        mean2 = random.randint(500, 700)
        std2 = random.randint(50, 200)
        ddl = random.randint(750, 900)
        cdf1 = st.norm(mean1, std1).cdf(ddl)
        cdf2 = st.norm(mean2, std2).cdf(ddl)
        if cdf1 > cdf2:
            n += 1
            if cdf1 - cdf2 < 0.05:
                n1 += 1
            if mean1 >= mean2:
                assert std1 < std2
            if std1 >= std2:
                assert mean1 < mean2
            ES1 = mean1 + std1 * st.norm.pdf(st.norm.ppf(cdf1)) / (1 - cdf1)
            ES2 = mean2 + std2 * st.norm.pdf(st.norm.ppf(cdf2)) / (1 - cdf2)
            if ES1 > ES2:
                print(ddl, [mean1, std1, cdf1, ES1], [mean2, std2, cdf2, ES2])
            assert ES1 < ES2
        else:
            n += 1
            if cdf2 - cdf1 < 0.05:
                n1 += 1
            if mean2 >= mean1:
                assert std2 < std1
            if std2 >= std1:
                assert mean2 < mean1
            ES1 = mean1 + std1 * st.norm.pdf(st.norm.ppf(cdf1)) / (1 - cdf1)
            ES2 = mean2 + std2 * st.norm.pdf(st.norm.ppf(cdf2)) / (1 - cdf2)
            if ES2 > ES1:
                print(ddl, [mean1, std1, cdf1, ES1], [mean2, std2, cdf2, ES2])
            assert ES2 < ES1
        print(f'test {n}({n1}) cases')
        print(ddl, [mean1, std1, cdf1, ES1], [mean2, std2, cdf2, ES2])


def get_time_std_from_speed_std():
    dist = 81.6
    speed_mean = 15.53
    speed_std = 12.00
    time_mean = dist / (0.44704 * speed_mean)
    time_std = time_mean * (speed_std / speed_mean) / 2
    print(f'time_mean: {time_mean}, time_std: {time_std}')


if __name__ == '__main__':
    # test_expected_shortfall()
    # test_monotonicity2()
    # get_time_std_from_speed_std()
    mean = 100
    std = 20
    quantile = 130
    cdf = round(st.norm(mean, std).cdf(quantile), 8)
    cdf2 = round(st.norm.cdf((quantile-mean)/std), 8)
    aa = st.norm.ppf(st.norm(mean, std).cdf(quantile))
    bb = (quantile-mean)/std
    print('cdf', cdf, cdf2, aa, bb)
    expected_shortfall = round(mean + std * st.norm.pdf(st.norm.ppf(cdf)) / (1 - cdf), 4) - quantile
    expected_shortfall2 = round(mean + std * st.norm.pdf((quantile-mean)/std) / (1 - cdf), 4) - quantile
    print('expected_shortfall', expected_shortfall, expected_shortfall2)

