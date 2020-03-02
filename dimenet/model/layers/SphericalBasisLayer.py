import sympy as sym
import tensorflow as tf
from tensorflow.keras import layers

from .basis_utils import bessel_basis, real_sph_harm
from .envelope import Envelope


class SphericalBasisLayer(layers.Layer):
    def __init__(self, num_spherical, num_radial, cutoff, envelope_exponent=5,
                 name='spherical_basis', **kwargs):
        super().__init__(name=name, **kwargs)

        assert num_radial <= 64
        self.num_radial = num_radial
        self.num_spherical = num_spherical

        self.inv_cutoff = tf.constant(1 / cutoff, dtype=tf.float32)
        self.envelope = Envelope(envelope_exponent)

        # retrieve formulas
        self.bessel_formulas = bessel_basis(num_spherical, num_radial)
        self.sph_harm_formulas = real_sph_harm(num_spherical)
        self.funcs = []

        # convert to tensorflow functions
        x = sym.symbols('x')
        theta = sym.symbols('theta')
        for i in range(num_spherical):
            for j in range(num_radial):
                self.funcs.append(sym.lambdify(
                    [x, theta], self.sph_harm_formulas[i][0] * self.bessel_formulas[i][j], 'tensorflow'))
    def call(self, inputs):
        d, Angles, id_expand_kj = inputs

        d_scaled = d * self.inv_cutoff
        d_scaled = tf.gather(d_scaled, id_expand_kj)

        rbf = [f(d_scaled, Angles) for f in self.funcs]
        rbf = tf.transpose(tf.stack(rbf))

        # Necessary for proper broadcasting behaviour
        d_scaled = tf.expand_dims(d_scaled, -1)

        d_cutoff = self.envelope(d_scaled)
