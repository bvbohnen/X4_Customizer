'''
Code for generation scaling equations, used by various transforms.
'''

'''
Fit function thoughts, made from the perspective of adjusting bullet speeds:

Simple formula: x*(y/(x+y))
 x = original damage
 y = tuning parameter
 For y=2000:
  x=2000 -> 1000 (slows down the sped up light weapons nicely)
  x=500  ->  400 (slows lower rate weapons less, though still a bit much)

Stronger formula: x*(y/(x+y))^z
 Since the (y/(x+y)) is effectively a scaling factor on the original damage, adding
 a power term 'z' should make that factor stronger the further it is below 1.
 For y=5000, z = 2
  x=2000 -> 1020
  x=500  ->  413 (not much better, would like to keep it 450+)
 Note that z < 0 also allows the equation to do have increasing returns by flipping
  the reduction factor over. Eg. 1/2 factor becomes (1/2)^-1 = 2

Can add an overall scaling term to correct the low end values back up:
 x*w*(y/(x+y))^z
 Where w,y,z are tuning parameters.
 The 'w' term can bring the 500 point back in line, and hopefully not effect lower
 points too much (there shouldn't be much below 300).

This was run through optimization, to get:
 w = 1.21
 y = 1.05e7
 z = 4.67e3
To keep some of the xrm speed, without also speeding up slow weapons too much, this
 can also aim for scaling x=2000 -> 1300 or so. This gives:
 w = 1.21
 y = 1.05e7
 z = 4.67e3
These parameters can be calculated dynamically before a transform uses them.


Question: can this same formula be used to increase small values while not increasing
large values, eg. with buffs to small weapons?
-The scaling term (y/(x+y)) can go from <1 to >1 with a negative power applied to it,
translating diminishing returns to increasing returns.
-Diminishing returns had y>>x : as x->0, scaling factor rises to 1.
-If y<<x, then as x->inf, scaling factor rises to 1.
Answer: in theory yes, it should work, with a small y and negative z.
-In practice, this found to have trouble getting a good fit, not nearly as 
 powerful as the diminishing returns style.
-Can only really solve for 1 data point well.
-The optimizer appears to try to 0 out the z term, leaving just a linear w term.
-This makes sense: as x increases, the scaling term will always diverge from 1,
 which is not what is wanted.

Can the function be flipped around in a way that will stabalize it for this case:
-Want small x to give a scaler far from 1, large x to converge on 1.
-Try: x*w*(x/(x+y))^z
-When x>>y, scaling goes to 1.
-When x~y, scaling goes to 1/2.

Result: the new equation (called 'reversed' below) works well for this case.


The above equations have a little bit of a problem with overshoot:
 If asked to scale the range 1 to 10 (to eg. 1 to 20), an outlier at 15
 might be excessively impacted (eg. yielding 100 instead of an expected 30).
This is a natural problem with these equations, that they are only smooth
in the range they are calibrated for.

To mitigate this overshoot problem, the calibrated equation will be packed
with a wrapper function that will check the input range, and will return
the calibrated scaling point nearest to the input if the input falls outside
the calibration range.
 Eg. if an equation is calibrated for 1 to 10, then seeing a 15 will cause
 the wrapped equation to return the scaling for 10, its nearest calibration
 point.


A problem exists with overflow in the fitting function when large values
are present.  To help stabalize against this, input terms will be scaled
to be close to 1, and the scaling term will be attached to the returned
scaling function to be automatically applied during evaluation.
'''
'''
Update:
    Scipy may not be installed for all users, and horrendously bloats any
    generated executable, so a backup will be used that does a simple
    linear scaling with bounds checks at the edges of the range.

    Eg. if the inputs are x = [100, 1000], y = [100, 500], then the
    scaling will be y = 100 + ((x - 100) * 500 / 900).
    Outside the 100,1000 range, ratios will use those edge points,
    eg. all inputs below 100 will be 1:1, all inputs above 1000
    will be 2:1.

    The general form of the equation will be:
    y = a + (x-b) * c
    Diminishing returns will have c <1; increasing returns will have c >1.

    Update:
    The above is actually not very good when looking at the plots.
    Something better might be more focused on scaling the multiplier,
    instead of the constant 'c' term used above.

    Can start with a term to capture where 'x' is between the min and
    max 'x' seen in the initial vectors.
        x_pos = (x - x_min) / (x_max - x_min)
            (eg. x = x_min, x_pos = 0; x = x_max, x_pos = 1)
    Can then determine the x:y ratios at x_min and x_max, and use
    the x position to transition from one to the other.
        scaling = (y_min / x_min) * (1 - x_pos) + (y_max / x_max) * (x_pos)
        y = x * scaling

    This new equation does have some oddity in that it can have a hump
    in the middle, where the transition between scaling ratios does
    not quite line up with the change in the x term, mostly because
    the x_min term is offset from 0.

    Eg. if x_min = 10, x_max = 30, y_min = 10, y_max = 15,
    then at a point x = 28:
        x_pos = 0.9
        scaling = 1*0.1 + 0.5*0.9 = .55
        y = 15.4, higher than y_max
    
    It is unclear on how to handle this; simply offsetting by x_min,
    and adding y_min to correct for a 0 term at x = x_min, causes
    large errors later (when the flat y_min hasn't been scaled).
    Simply limiting the result to the [y_min, y_max] range would
    cause flat portions in the plot, where the input x changing
    has no effect.

    TODO: spend some more thought on this. Stick with the simple
    equation for now, since at least it does not have humps.

'''
import math
from Common.Settings import Settings

# Conditional import of scipy.
try:
    import scipy.optimize as optimize
    Scipy_available = True
except:
    Scipy_available = False


class Scaling_Function():
    '''
    Scaling function wrapper class.
    Records the base equation, coefficients, and valid range.
    May be called like a normal function, providing the input to scale.
    '''
    def __init__(self, scaling_func, coefs, x_vec, x_scaling = 1, y_scaling = 1):

        # Record the input scaling factors for x and y.
        # These are determined during function selection and fitting,
        #  and get applied during evaluation.
        self.x_scaling = x_scaling
        self.y_scaling = y_scaling

        # Record the central scaling python function, and the
        #  coefs determined for it.
        self.scaling_func = scaling_func
        self.coefs = coefs

        # Record the x input range.
        self.x_min = min(x_vec)
        self.x_max = max(x_vec)

        # Record the min/max y points as well, taken from the
        #  scaling function selected.
        self.y_min = self.scaling_func(self.x_min, *s.coefs)
        self.y_max = self.scaling_func(self.x_max, *s.coefs)

        # Record the min/max y/x ratios.
        self.yx_ratio_min = self.y_min / self.x_min
        self.yx_ratio_max = self.y_max / self.x_max
        return

    # Provide the call wrapper.
    def __call__(self, x):
        # Apply the x_scaling to the input.
        x = x * self.x_scaling
        # Check for x out of the calibration bounds, and use
        #  the nearest bound's y/x ratio if so.
        if x > self.x_max:
            # Don't want to return the actual y_max, since the out of
            #  range x should still be getting proportionally scaled.
            #  Eg. if x = 2*x_max, and y_max = x_max, then want y = 2*x.
            # Multiply x by the max y/x ratio.
            y_scaled = x * self.yx_ratio_max
        elif x < self.x_min:
            y_scaled = x * self.yx_ratio_min
        else:
            # Run the scaling func on it.
            y_scaled = self.scaling_func(x, *s.coefs)
        # Unscale and return.
        # (Could probably flip the y_scaling and just do a mult, but speed
        #  doesn't matter.)
        y = y_scaled / self.y_scaling
        return y


# Fit function
def Fit_equation(x, a,b,c):
    'Standard smoothed scaling equation, for scipy optimization'
    # Do some bounds checking.
    # a,b should never be negative.
    if a<0 or b<0:
        # Return a silly number to discourage the optimizer.
        return float('inf')
    # Use the version stable at low x.
    return x *a *((b / (x+b))**c)


def Fit_equation_reversed(x, a,b,c):
    'Reversed smoothed scaling equation, for scipy optimization'
    if a<0 or b<0:
        return float('inf')
    # Use the version stable at high x.
    return x *a *((x / (x+b))**c)


def Fit_equation_simple(x, a,b,c):
    'Super simple linear scaling equation.'
    # Don't need to worry about inf on this, since it won't be
    #  fed to scipy.
    return a + (x - b) * c


def Fit_equation_linear(x, x_min, x_max, y_min, y_max):
    'More advanced linear scaling equation.'
    x_pos = (x - x_min) / (x_max - x_min)
    scaling = (y_min / x_min) * (1 - x_pos) + (y_max / x_max) * (x_pos)
    return y_min + (x - x_min) * scaling


def Get_Scaling_Fit(x_vec, y_vec, **kwargs):
    '''
    Returns a function-like Scaling_Function class object.
    If (y < x) in general, a diminishing formula is used, otherwise
     and increasing formula is used.
    If the largest changes occur near the low x, smallest
     changes at high x, a reversed scaling formula is used.
    If scipy is selected in settings and importable, a smooth function
     will be used for scaling, else a linear function is used.
    '''
    if Scipy_available and Settings.use_scipy_for_scaling_equations:
        fit_equation = Get_Scipy_Scaling_Fit(x_vec, y_vec, **kwargs)
    else:
        fit_equation = Get_Linear_Scaling_Fit(x_vec, y_vec, **kwargs)
        # TODO: maybe give a nice message if scipy was requested and
        # is not available.
    
    # Calculate the data points for debug check.
    #final_y_vec = [fit_equation(x) for x in x_vec]

    # Optionally plot the equation.
    if Settings.show_scaling_plots:
        print('x:', x_vec)
        print('y:', y_vec)
        # For debug, view the curve to see if it looks as expected.
        Plot_Fit(fit_equation)

    return fit_equation


def Get_Linear_Scaling_Fit(x_vec, y_vec, **kwargs):
    '''
    Returns a function-like Scaling_Function class object, using a
    simple linear equation.
    '''
    # This will only look at the min and max points; intermediate
    #  values may be present to help scipy fit the middle part
    #  of its equation, but that doesnt matter for linear.
    x_min_index = x_vec.index( min(x_vec))
    x_max_index = x_vec.index( max(x_vec))

    # Calculate the equation terms.
    if 1:
        # Super simple scaling function.
        scaling_func = Fit_equation_simple
        # Min x will be shifted to 0 by subtracting 'b'.
        b = x_vec[x_min_index]
        # Corresponding min y gets added back in as 'a'.
        a = y_vec[x_min_index]
        # Max x translates to max y using a restructured form of
        #  the equation: c = (y_max - a) / (x_max - b)
        c = (y_vec[x_max_index] - a) / (x_vec[x_max_index] - b)
        coefs = (a,b,c)
    else:
        # More complex equation.
        # Has some overshoot issues.
        scaling_func = Fit_equation_linear
        # Takes the min/max x and corresponding y.
        coefs = (x_vec[x_min_index], 
                 x_vec[x_max_index], 
                 y_vec[x_min_index], 
                 y_vec[x_max_index])

    # Set up the function.
    fit_equation = Scaling_Function(
        scaling_func = scaling_func, 
        coefs = coefs, 
        x_vec = x_vec
        )

    return fit_equation


def Get_Scipy_Scaling_Fit(x_vec, y_vec, **kwargs):
    '''
    Returns a function-like Scaling_Function class object, using
    scipy for a smooth equation.
    '''
    # Rescale the inputs to place them close to 1.
    # This can be done later, before fitting, but is easiest if
    #  done early always.
    x_vec, x_scaling = Rescale_Vec(x_vec)
    y_vec, y_scaling = Rescale_Vec(y_vec)

    # Do a test on the inputs to figure out if this is in diminishing or 
    #  increasing returns mode.
    diminishing_mode = True
    # Check all data points summed up, and compare.
    if sum(y_vec) > sum(x_vec):
        # If y>x, not diminishing.
        diminishing_mode = False


    # Pick the fit equation to use. Select this automatically based
    #  on the input values (eg. is the bigger change on the small side or
    #  the large side).
    # Get the smallest x indices.
    x_min_index = x_vec.index( min(x_vec))
    x_max_index = x_vec.index( max(x_vec))
    # Get the ratio of x/y at the small and large points.
    x_min_to_y = x_vec[x_min_index] / y_vec[x_min_index]
    x_max_to_y = x_vec[x_max_index] / y_vec[x_max_index]

    # Default to standard equation.
    reverse = False
    # When in diminishing mode, if the max x/y is smaller than the
    #  min x/y, then use the reverse formula.
    if diminishing_mode and x_max_to_y < x_min_to_y:
        reverse = True
    # When in increasing mode, if the max x/y is larger than the
    #  min x/y, then reverse.
    if not diminishing_mode and x_max_to_y > x_min_to_y:
        reverse = True
    
    # Pick the equation to use.
    fit_equation_to_use = Fit_equation
    if reverse:
        fit_equation_to_use = Fit_equation_reversed
        

    # Curve fit entry function (gets the full x vector, returns y vector).
    def curve_fit_entry_func(x_vec, *coefs):
        y = []
        for x in x_vec:
            y.append(fit_equation_to_use(x, *coefs))
        return y


    def minimize_entry_func(coefs, x_vec, y_vec):
        # Get a vectors of values using these coefs.
        y_new = [fit_equation_to_use(x,*coefs) for x in x_vec]
                
        # Aim to minimize the ratio differences in y.
        # -Removed in favor of SAD; also, this had a spurious divide
        #  by 0 warning (maybe for missile damage scaling).
        ##Get ratio in both directions, take the max of either.
        ##Eg. 1/2 and 2/1 will both evaluate to 2.
        # diffs = [max(y0/y1, y1/y0) for y0, y1 in zip(y_new, y_vec)]
        ##Could optionally increase the weight on large diffs, eg. by
        ## squaring.
        # diffs = [d**2 for d in diffs]
        # error = sum(diffs)

        # Can also try sum of least squares style.
        sad = sum([(y0 - y1) **2 for y0, y1 in zip(y_new, y_vec)])

        # return error
        return sad


    # Find initial coefs.
    '''
    These can set w and z to 1, y to whatever satisfies the first data pair.
    Eg. y = x*b/(x+b), solve for b.
     yx + yb = xb
     yx = b(x-y)
     yx/(x-y) = b

    Sanity check: if y = 0.5, x = 1, then b = 1 to divide properly. Checks out in both eqs.

    What if y==x at this point?  Would get divide by 0.
    -Try all points until one does not divide by 0.
    -If such a point not found, all data is equal, and can set b0 to some very high number,
     higher than anything in the x vector (50x should do).

    What is y>x, such that b is negative?
    -Leads to a math domain error when optimizing, in practice, since the power term is
     operating on a negative, eg (-1)^c.
    -If y = 1, x = 0.5, then b = -1.
    -The expected fix for this is to have the overall power term be negative, eg. -1, so that
     the equation to solve is y = x*(x+b)/b.
     yb = xx + xb
     yb - xb = xx
     b = xx / (y-x)
     Sanity check: if y = 1, x = 0.5, then b = 0.5.

    Can look at the vector data to determine which mode is expected, and set the coefs
    accordingly.
    '''
    
    # Find b0 and z0 based on mode.
    if diminishing_mode:
        z0 = 1
        # Start b0 at something higher than anything in x, in case
        #  all data points are the same.
        b0 = 50 * max(x_vec)
        # Calc b for the first mismatched data points.
        for x,y in zip(x_vec, y_vec):
            if x != y:
                b0 = y * x / (x - y)
                break
        # Set the bounds for the coefs.
        # Force a,b to be positive, but allow z to go negative.
        coef_bounds = [(0,None),(0,None),(-5,5)]
    else:
        z0 = -1
        # Start b0 at something lower than anything in x.
        b0 = min(x_vec) / 50
        # Calc b for the first mismatched data points.
        for x,y in zip(x_vec, y_vec):
            if x != y:
                b0 = x * x / (y - x)
                break
        # Set the bounds for the coefs.
        coef_bounds = [(0,None),(0,None),(-5,5)]
    coefs_0 = [1,b0,z0]


    # Do curve fit.
    # -Removed, couldn't handle increasing returns cases, probably because of
    #  lack of staying in bounds (keeps making b negative).
    # coefs, _ = optimize.curve_fit(curve_fit_entry_func, x_vec, y_vec, coefs_0)

    # Use minimize instead.
    # This aims to minimize a single value returned by the target function.
    optimize_result = optimize.minimize(
        # Objective function; should return a scaler value to minimize.
        # Eg. calculate speeds, take difference from the original speeds, return
        #  some estimate of error (eg. max difference).
        fun = minimize_entry_func,
        # Starting guess
        x0 = coefs_0,
        # Pass as args the x and y data.
        args = (x_vec, y_vec),
        # Use default solver for now.
        # Set the bounds.
        bounds = coef_bounds
        )
    coefs = optimize_result.x

    # Make the scaling function object.
    fit_equation = Scaling_Function( 
        fit_equation_to_use, coefs, x_vec, x_scaling, y_scaling)

    return fit_equation


def Rescale_Vec(vec):
    'Scale a vector so that its values are centered around 1.'
    # This can be based off of the average value in the input.
    # return vec, 1 #Test return.
    avg = sum(vec)/len(vec)
    scaling = 1/avg
    new_vec = [x*scaling for x in vec]
    return new_vec, scaling


def Plot_Fit(fit_equation):
    'Make a plot of this fit.'
    # Try to find matplotlib, and numpy as well.
    try:
        import matplotlib.pyplot
        import numpy
    except:
        print('Skipping scaling equation plot; numy or matplotlib missing.')
        return

    # Plot over the full range, plus an extra 10% on each side to see
    #  if the limiter is working.
    # Treat the x inputs as original values to be scaled (eg. take the
    #  internal x_min/x_max and unscale them first).
    x_spaced = numpy.linspace(fit_equation.x_min * 0.9 / fit_equation.x_scaling, 
                              fit_equation.x_max * 1.1 / fit_equation.x_scaling, 
                              50)
    y_spaced = [fit_equation(x) for x in x_spaced]
    plot = matplotlib.pyplot.plot(x_spaced, y_spaced)
    matplotlib.pyplot.show()
    return