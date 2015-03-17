from helpers import *
from lasagne import *

class ReshapeLayer(layers.Layer):
    """
    A layer reshaping its input tensor to another tensor of the same total
    number of elements.
    :parameters:
        - incoming : a :class:`Layer` instance or a tuple
            the layer feeding into this layer, or the expected input shape
        - shape : tuple
            The target shape specification. Any of its elements can be `[i]`,
            a single-element list of int, denoting to use the size of the ith
            input dimension. At most one element can be `-1`, denoting to
            infer the size for this dimension to match the total number of
            elements of the input tensor. Any remaining elements must be
            positive integers directly giving the size of the corresponding
            dimension.
    :usage:
        >>> from lasagne.layers import InputLayer, ReshapeLayer
        >>> l_in = InputLayer((None, 100, 20))
        >>> l1 = ReshapeLayer(l_in, ([0], [1], 2, 10))
        >>> l1.get_output_shape()
        (None, 100, 2, 10)
        >>> l2 = ReshapeLayer(l_in, ([0], 1, 2, 5, -1))
        >>> l2.get_output_shape()
        (None, 1, 2, 5, 200)
    :note:
        The tensor elements will be fetched and placed in C-like order. That
        is, reshaping `[1,2,3,4,5,6]` to shape `(2,3)` will result in a matrix
        `[[1,2,3],[4,5,6]]`, not in `[[1,3,5],[2,4,6]]` (Fortran-like order),
        regardless of the memory layout of the input tensor. For C-contiguous
        input, reshaping is cheap, for others it may require copying the data.
    """

    def __init__(self, incoming, shape, **kwargs):
        super(ReshapeLayer, self).__init__(incoming, **kwargs)
        shape = tuple(shape)
        for s in shape:
            if isinstance(s, int):
                if s == 0 or s < - 1:
                    raise ValueError("`shape` integers must be positive or -1")
            elif isinstance(s, list):
                if len(s) != 1 or not isinstance(s[0], int) or s[0] < 0:
                    raise ValueError("`shape` input references must be "
                                     "single-element lists of int >= 0")
            else:
                raise ValueError("`shape` must be a tuple of int and/or [int]")
        if sum(s == -1 for s in shape) > 1:
            raise ValueError("`shape` cannot contain multiple -1")
        self.shape = shape

    def get_output_shape_for(self, input_shape, *args, **kwargs):
        # Initialize output shape from shape specification
        output_shape = list(self.shape)
        # First, replace all `[i]` with the corresponding input dimension, and
        # mask parts of the shapes thus becoming irrelevant for -1 inference
        masked_input_shape = list(input_shape)
        masked_output_shape = list(output_shape)
        for dim, o in enumerate(output_shape):
            if isinstance(o, list):
                if o[0] >= len(input_shape):
                    raise ValueError("specification contains [%d], but input "
                                     "shape has %d dimensions only" %
                                     (o[0], len(input_shape)))
                output_shape[dim] = input_shape[o[0]]
                masked_output_shape[dim] = input_shape[o[0]]
                if ((input_shape[o[0]] is None)
                    and (masked_input_shape[o[0]] is None)):
                    # first time we copied this unknown input size: mask it, we
                    # have a 1:1 correspondence between out[dim] and in[o[0]]
                    # and can ignore it for -1 inference even if it is unknown.
                    masked_input_shape[o[0]] = 1
                    masked_output_shape[dim] = 1
        # From the shapes, compute the sizes of the input and output tensor
        input_size = (None if any(x is None for x in masked_input_shape)
                      else np.prod(masked_input_shape))
        output_size = (None if any(x is None for x in masked_output_shape)
                       else np.prod(masked_output_shape))
        del masked_input_shape, masked_output_shape
        # Finally, infer value for -1 if needed
        if -1 in output_shape:
            dim = output_shape.index(-1)
            if (input_size is None) or (output_size is None):
                output_shape[dim] = None
                output_size = None
            else:
                output_size *= -1
                output_shape[dim] = input_size // output_size
                output_size *= output_shape[dim]
        # Sanity check
        if ((input_size is not None) and (output_size is not None)
            and (input_size != output_size)):
            raise ValueError("%s cannot be reshaped to specification %s. "
                             "The total size mismatches." %
                             (input_shape, self.shape))
        return tuple(output_shape)

    def get_output_for(self, input, *args, **kwargs):
        # Replace all `[i]` with the corresponding input dimension
        output_shape = list(self.shape)
        for dim, o in enumerate(output_shape):
            if isinstance(o, list):
                output_shape[dim] = input.shape[o[0]]
        # Everything else is handled by Theano
        return input.reshape(tuple(output_shape))
