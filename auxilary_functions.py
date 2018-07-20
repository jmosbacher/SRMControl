import numpy as np
#import cv2
#import opencv as cv2

def length_of(attr):
    def length(self):
        return len(getattr(self,attr))
    return length

# def rotate_image(image, angle):
#   image_center = tuple(np.array(image.shape)/2)
#   rot_mat = cv2.getRotationMatrix2D(image_center,angle,1.0)
#   result = cv2.warpAffine(image, rot_mat, image.shape)#,flags=cv2.INTER_LINEAR
#   return result


def multi_for(iterables):
    if not iterables:
        yield ()
    else:
        for item in iterables[0]:
            for rest_tuple in multi_for(iterables[1:]):
                yield (item,) + rest_tuple


def multi_enum(iterables):
    if not iterables:
        yield (), ()
    else:
        for n,item in enumerate(iterables[0]):
            for ns, rest_tuple in multi_enum(iterables[1:]):
                yield (n,)+ns, (item,)+rest_tuple



def progress_bar( nmin=0.0, nmax=100.0, nsymb=10, show_perc=True,
                  left_symb=u'\u2592', done_symb=u'\u2593'):
    """
    Parameters
    ----------
    nmin : float
        Number to associate with 0% progress.
    nmax : float
        Number to associate with 100% progress.
    nsymb : int
        Total number of symbols to draw
    show_perc : bool
        symbol to represent done parts
    left_symb : unicode
        symbol to represent unfinished parts
    done_symb : unicode
    Returns
    -------
    callable
        a rendering function that produces
         a unicode string from a int/float.
    """
    def render_prog_str(n):
        if not isinstance(n, (int,float)):
            return u''

        frac = (n-nmin)/(nmax-nmin)
        perc = int(frac * 100)
        if n>=nmax:
            ndone = nsymb
            perc = 100
        else:
            ndone = int(frac * nsymb)
        if n<=nmin:
            nleft = nsymb
            perc = 0
        else:
            nleft = nsymb - ndone
        parts = [done_symb for i in range(ndone)]
        parts += [left_symb for i in range(nleft)]
        if show_perc:
            parts.append(u' {}%'.format(int(perc)))
        return u''.join(parts)
    return render_prog_str

def format_truth(t):
    if t:
        return u'\u2714'
    else:
        return u'\u2718'

if __name__=='__main__':
    a = np.arange(10)
    b = np.arange(10,20)
    h = np.arange(20,30)
    t = [[1]]*10
    def tester():
        yield 'test'
    t.append(a)
    t.append(tester())
    from itertools import product
    for n in product(*t):
        print(n)
    #for n,(c,t) in enumerate(multi_enum([a,b,h])):
        #print n,c, t

