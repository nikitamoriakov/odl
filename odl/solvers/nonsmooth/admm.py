"""Alternating Direction method of Multipliers (ADMM) method variants."""

from __future__ import division
from odl.operator import Operator


__all__ = ('admm_linearized',)


def admm_linearized(x, f, g, L, tau, sigma, niter, **kwargs):
    """Generic linearized ADMM method for convex problems.

    ADMM stands for "Alternating Direction Method of Multipliers" and
    is a popular convex optimization method. This variant solves problems
    of the form ::

        min_x [ f(x) + g(Lx) ]

    with convex ``f`` and ``g``, and a linear operator ``L``. See Section
    4.4 of `[PB2014] <http://web.stanford.edu/~boyd/papers/prox_algs.html>`_
    and the Notes for more mathematical details.

    Parameters
    ----------
    x : ``L.domain`` element
        Starting point of the iteration, updated in-place.
    f, g : `Functional`
        The functions ``f`` and ``g`` in the problem definition. They
        need to implement the ``proximal`` method.
    L : linear `Operator`
        The linear operator that should be applied before ``f``. Its range
        must match the domain of ``f``, and its domain must match the domain
        of ``g``.
    tau, sigma : positive float
        Step size parameters for the update of the variables.
    niter : non-negative int
        Number of iterations.

    Other Parameters
    ----------------
    callback : callable, optional
        Function called with the current iterate after each iteration.

    Notes
    -----
    The ADMM method applies the following iteration:

    .. math::
        x^{(k+1)} &= \mathrm{prox}_{\\tau f} \\left[
            x^{(k)} - \sigma^{-1}\\tau L^*\\big(
                L x^{(k)} - z^{(k)} + u^{(k)}
            \\big)
        \\right]

        z^{(k+1)} &= \mathrm{prox}_{\sigma g}\\left(
            L x^{(k+1)} + u^{(k)}
        \\right)

        u^{(k+1)} &= u^{(k)} + L x^{(k+1)} - z^{(k+1)}

    The step size parameters :math:`\\tau` and :math:`\sigma` must satisfy

    .. math::
        0 < \\tau < \\frac{\sigma}{\|L\|^2}

    to guarantee convergence.

    The name "linearized ADMM" comes from the fact that in the
    minimization subproblem for the :math:`x` variable, this variant
    uses a linearization of a quadratic term in the augmented Lagrangian
    of the generic ADMM, in order to make the step expressible with
    the proximal operator of :math:`f`.

    Another name for this algorithm is *split inexact Uzawa method*.

    References
    ----------
    [PB2014] Parikh, N and Boyd, S. *Proximal Algorithms*. Foundations and
    Trends in Optimization, 1(3) (2014), pp 123-231.
    """
    # Forward operator
    if not isinstance(L, Operator):
        raise TypeError('`op` {!r} is not an `Operator` instance'
                        ''.format(L))

    # Starting point
    if x not in L.domain:
        raise TypeError('`x` {!r} is not in the domain of `op` {!r}'
                        ''.format(x, L.domain))

    # Step size parameter
    tau, tau_in = float(tau), tau
    if tau <= 0:
        raise ValueError('`tau` must be positive, got {}'.format(tau_in))

    # Step size parameter
    sigma, sigma_in = float(sigma), sigma
    if sigma <= 0:
        raise ValueError('`sigma` must be positive, got {}'.format(sigma_in))

    # Number of iterations
    if not isinstance(niter, int) or niter < 0:
        raise ValueError('`niter` {} not understood'
                         ''.format(niter))

    # Callback object
    callback = kwargs.pop('callback', None)
    if callback is not None and not callable(callback):
        raise TypeError('`callback` {} is not callable'.format(callback))

    # Initialize range variables
    z = L.range.zero()
    u = L.range.zero()

    # Temporary for Lx + u [- z]
    tmp_ran = L(x)
    # Temporary for L^*(Lx + u - z)
    tmp_dom = L.domain.element()

    for _ in range(niter):
        # tmp_ran has value L x^k here
        # tmp_dom <- L^*(L x^k + u^k - z^k)
        tmp_ran += u
        tmp_ran -= z
        L.adjoint(tmp_ran, out=tmp_dom)

        # x <- x^k - (tau/sigma) L^*(Lx^k + u^k - z^k)
        x.lincomb(1, x, -tau / sigma, tmp_dom)
        # x^(k+1) <- prox[tau*f](x)
        f.proximal(tau)(x, out=x)

        # tmp_ran <- L x^(k+1)
        L(x, out=tmp_ran)
        # z^(k+1) <- prox[sigma*g](L x^(k+1) + u^k)
        g.proximal(sigma)(tmp_ran + u, out=z)  # 1 copy here

        # u^(k+1) = u^k + L x^(k+1) - z^(k+1)
        u += tmp_ran
        u -= z

        if callback is not None:
            callback(x)


def admm_linearized_simple(x, f, g, L, tau, sigma, niter, **kwargs):
    """Non-optimized version of ``admm_linearized``.

    This function is intended for debugging. It makes a lot of copies and
    performs no error checking.
    """
    callback = kwargs.pop('callback', None)
    z = L.range.zero()
    u = L.range.zero()
    for _ in range(niter):
        x[:] = f.proximal(tau)(x - tau / sigma * L.adjoint(L(x) + u - z))
        z = g.proximal(sigma)(L(x) + u)
        u = L(x) + u - z
        if callback is not None:
            callback(x)
