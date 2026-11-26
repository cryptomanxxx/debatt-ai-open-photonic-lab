'use strict';

const Chip16Model = (() => {
  const EPS = 1e-12;
  const rayOffsets = [-16, -8, 0, 8, 16];
  const defaults = {
    x: -5, y: 0, angle: 0, bits: 5,
    a: {x: 1.5, y: 0, w: 2.4, h: 2.4},
    b: {x: 4.2, y: -2.3, w: 1.8, h: 1.6},
  };

  // Intersect the two axis intervals with the forward half-line t ≥ 0.
  function intersection(origin, direction, min, max) {
    if (direction.every(value => Math.abs(value) < EPS)) return null;
    let entry = 0;
    let exit = Infinity;
    for (let axis = 0; axis < origin.length; axis++) {
      const velocity = direction[axis];
      if (Math.abs(velocity) < EPS) {
        if (origin[axis] < min[axis] || origin[axis] > max[axis]) return null;
        continue;
      }
      const left = (min[axis] - origin[axis]) / velocity;
      const right = (max[axis] - origin[axis]) / velocity;
      entry = Math.max(entry, Math.min(left, right));
      exit = Math.min(exit, Math.max(left, right));
      if (exit < entry) return null;
    }
    return {entry, exit};
  }

  function bounds(box) {
    return {
      min: [box.x - box.w / 2, box.y - box.h / 2],
      max: [box.x + box.w / 2, box.y + box.h / 2],
    };
  }

  function compare(origin, direction, box, bits) {
    const {min, max} = bounds(box);
    const scale = 2 ** bits;
    const round = value => Math.round(value * scale) / scale;
    const rounded = {
      origin: origin.map(round), direction: direction.map(round),
      min: min.map(round), max: max.map(round),
    };
    const exact = intersection(origin, direction, min, max);
    const proxy = intersection(rounded.origin, rounded.direction, rounded.min, rounded.max);
    const status = exact ? (proxy ? 'hit' : 'fn') : (proxy ? 'fp' : 'miss');
    return {exact, proxy, status, rounded};
  }

  function rays(settings, box) {
    const origin = [settings.x, settings.y];
    return rayOffsets.map(offset => {
      const angle = settings.angle + offset;
      const rad = angle * Math.PI / 180;
      const direction = [Math.cos(rad), Math.sin(rad)];
      return {angle, origin, direction, ...compare(origin, direction, box, settings.bits)};
    });
  }

  // Equation 1 readout with unit reference and small, dimensionless input phases.
  // The coefficients are a 2D point-side example, not 3D ray/edge coordinates.
  function opticalSide(origin, direction, point) {
    const [r1, r2] = [-direction[1], direction[0]];
    const [v1, v2] = point.map((value, axis) => (value - origin[axis]) / 16);
    const side = r1 * v1 + r2 * v2;
    const branch1 = Math.sin(r1 / 4) * Math.sin(v1 / 4);
    const branch2 = Math.sin(r2 / 4) * Math.sin(v2 / 4);
    const field = 1 + branch1 + branch2;
    return {side, branch1, branch2, field, delta: field ** 2 - 1};
  }

  return {defaults, intersection, bounds, compare, rays, opticalSide};
})();
if (typeof module !== 'undefined') module.exports = Chip16Model;
