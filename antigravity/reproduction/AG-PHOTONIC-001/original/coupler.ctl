; Parameterized MPB directional coupler solver
; Units: micrometers (a = 1 um), lambda0 = 1.55 um
(define-param res 64)
(define-param sx 6.0)
(define-param sy 4.0)
(define-param w 0.45)
(define-param h 0.22)
(define-param gap 0.20)

(set-param! resolution res)
(set! geometry-lattice (make lattice (size sx sy no-size)))

(define Si (make dielectric (index 3.48)))
(define SiO2 (make dielectric (index 1.44)))
(set! default-material SiO2)

(define x0 (* 0.5 (+ w gap)))

(set! geometry
  (list
    (make block (center (- x0) 0 0) (size w h infinity) (material Si))
    (make block (center x0 0 0) (size w h infinity) (material Si))
  )
)

(set! num-bands 2)
(define omega (/ 1.0 1.55))

(find-k NO-PARITY omega 1 2 (vector3 0 0 1) 1e-7 (* omega 2.35) (* omega 1.44) (* omega 3.48)
  (lambda (band)
    (get-efield band)
    (let* ((ec (get-field-point (vector3 0 0 0)))
           (ew (get-field-point (vector3 x0 0 0)))
           (ex-c (magnitude (vector3-x ec)))
           (ex-w (magnitude (vector3-x ew)))
           (ey-w (magnitude (vector3-y ew)))
           (neff (/ (vector3-z current-k) omega)))
      (print "RESULT:, gap=" gap ", res=" res ", sx=" sx ", sy=" sy
             ", band=" band ", neff=" neff
             ", |Ex(0)|=" ex-c ", |Ex(x0)|=" ex-w ", |Ey(x0)|=" ey-w "\n")
    )
  )
)
