import numpy as np

from ffedge.adp_model import p_gone_by, p_gone_by_array, sigma_for, norm_cdf


def test_sigma_grows_and_caps():
    assert sigma_for(1) < sigma_for(20) < sigma_for(100)
    assert sigma_for(400, 500) == 35.0


def test_norm_cdf_matches_erf():
    from math import erf, sqrt
    xs = np.array([-2.0, -0.5, 0.0, 0.7, 2.5])
    ref = np.array([0.5 * (1 + erf(x / sqrt(2))) for x in xs])
    assert np.allclose(norm_cdf(xs), ref, atol=2e-7)


def test_p_gone_by_monotone_and_bounds():
    assert p_gone_by(20, 4, 4, 4) == 0.0
    a = p_gone_by(20, 4, 4, 15)
    b = p_gone_by(20, 4, 4, 21)
    c = p_gone_by(20, 4, 4, 40)
    assert 0 <= a < b < c <= 1.0
    assert c > 0.99


def test_conditioning_on_availability():
    # A player with ADP 5 still available at pick 20 is nearly certain to go before 28
    assert p_gone_by(5, 2, 20, 28) > 0.99
    # Vector version agrees with scalar
    adp = np.array([5.0, 20.0, 60.0]); sig = np.array([2.0, 4.0, 10.0])
    v = p_gone_by_array(adp, sig, 4, 21)
    for i in range(3):
        assert abs(v[i] - p_gone_by(adp[i], sig[i], 4, 21)) < 1e-6
