import datetime
import decimal
import sys
import unittest
from ctypes import (byref, c_byte, c_char, c_double, c_float, c_int, c_int64, c_short,
                    c_ubyte, c_uint, c_uint64, c_ushort, POINTER, pointer)

from comtypes import GUID, IUnknown
from comtypes.automation import (DISPPARAMS, VARIANT, VT_BSTR, VT_BYREF, VT_CY, VT_DATE,
                                 VT_DECIMAL, VT_EMPTY, VT_ERROR, VT_I1, VT_I2, VT_I4,
                                 VT_I8, VT_NULL, VT_R4, VT_R8, VT_UI1, VT_UI2, VT_UI4,
                                 VT_UI8)
from comtypes.test import get_numpy
from comtypes.test.find_memleak import find_memleak
from comtypes.typeinfo import LoadRegTypeLib


def get_refcnt(comptr):
    # return the COM reference count of a COM interface pointer
    if not comptr:
        return 0
    comptr.AddRef()
    return comptr.Release()


class VariantTestCase(unittest.TestCase):

    def test_constants(self):
        empty = VARIANT.empty
        self.failUnlessEqual(empty.vt, VT_EMPTY)
        self.failUnless(empty.value is None)

        null = VARIANT.null
        self.failUnlessEqual(null.vt, VT_NULL)
        self.failUnless(null.value is None)

        missing = VARIANT.missing
        self.failUnlessEqual(missing.vt, VT_ERROR)
        self.assertRaises(NotImplementedError, lambda: missing.value)

    def test_com_refcounts(self):
        # typelib for oleaut32
        tlb = LoadRegTypeLib(GUID("{00020430-0000-0000-C000-000000000046}"), 2, 0, 0)
        rc = get_refcnt(tlb)

        p = tlb.QueryInterface(IUnknown)
        self.failUnlessEqual(get_refcnt(tlb), rc+1)

        del p
        self.failUnlessEqual(get_refcnt(tlb), rc)

    def test_com_pointers(self):
        # Storing a COM interface pointer in a VARIANT increments the refcount,
        # changing the variant to contain something else decrements it
        tlb = LoadRegTypeLib(GUID("{00020430-0000-0000-C000-000000000046}"), 2, 0, 0)
        rc = get_refcnt(tlb)

        v = VARIANT(tlb)
        self.failUnlessEqual(get_refcnt(tlb), rc+1)

        p = v.value
        self.failUnlessEqual(get_refcnt(tlb), rc+2)
        del p
        self.failUnlessEqual(get_refcnt(tlb), rc+1)

        v.value = None
        self.failUnlessEqual(get_refcnt(tlb), rc)

    def test_null_com_pointers(self):
        p = POINTER(IUnknown)()
        self.failUnlessEqual(get_refcnt(p), 0)

        VARIANT(p)
        self.failUnlessEqual(get_refcnt(p), 0)

    def test_dispparams(self):
        # DISPPARAMS is a complex structure, well worth testing.
        d = DISPPARAMS()
        d.rgvarg = (VARIANT * 3)()
        values = [1, 5, 7]
        for i, v in enumerate(values):
            d.rgvarg[i].value = v
        result = [d.rgvarg[i].value for i in range(3)]
        self.failUnlessEqual(result, values)

    def test_pythonobjects(self):
        objects = [None, 42, 3.14, True, False, "abc", u"abc", 7L]
        for x in objects:
            v = VARIANT(x)
            self.failUnlessEqual(x, v.value)

    def test_integers(self):
        v = VARIANT()

        if (hasattr(sys, "maxint")):
            # this test doesn't work in Python 3000
            v.value = sys.maxint
            self.failUnlessEqual(v.value, sys.maxint)
            self.failUnlessEqual(type(v.value), int)

            v.value += 1
            self.failUnlessEqual(v.value, sys.maxint+1)
            self.failUnlessEqual(type(v.value), long)

        v.value = 1L
        self.failUnlessEqual(v.value, 1)
        self.failUnlessEqual(type(v.value), int)

    def test_datetime(self):
        now = datetime.datetime.now()

        v = VARIANT()
        v.value = now
        self.failUnlessEqual(v.vt, VT_DATE)
        self.failUnlessEqual(v.value, now)

    def test_datetime64(self):
        np = get_numpy()
        if np is None:
            return
        try:
            np.datetime64
        except AttributeError:
            return

        dates = [
            np.datetime64("2000-01-01T05:30:00", "s"),
            np.datetime64("1800-01-01T05:30:00", "ms"),
            np.datetime64("2000-01-01T12:34:56", "us")
        ]

        for date in dates:
            v = VARIANT()
            v.value = date
            self.failUnlessEqual(v.vt, VT_DATE)
            self.failUnlessEqual(v.value, date.astype(datetime.datetime))

    def test_decimal_as_currency(self):
        value = decimal.Decimal('3.14')

        v = VARIANT()
        v.value = value
        self.failUnlessEqual(v.vt, VT_CY)
        self.failUnlessEqual(v.value, value)

    def test_decimal_as_decimal(self):
        v = VARIANT()
        v.vt = VT_DECIMAL
        v.decVal.Lo64 = 1234
        v.decVal.scale = 3
        self.failUnlessEqual(v.value, decimal.Decimal('1.234'))

        v.decVal.sign = 0x80
        self.failUnlessEqual(v.value, decimal.Decimal('-1.234'))

        v.decVal.scale = 28
        self.failUnlessEqual(v.value, decimal.Decimal('-1.234e-25'))

        v.decVal.scale = 12
        v.decVal.Hi32 = 100
        self.failUnlessEqual(
            v.value, decimal.Decimal('-1844674407.370955162834'))

    def test_BSTR(self):
        v = VARIANT()
        v.value = u"abc\x00123\x00"
        self.failUnlessEqual(v.value, "abc\x00123\x00")

        v.value = None
        # manually clear the variant
        v._.VT_I4 = 0

        # NULL pointer BSTR should be handled as empty string
        v.vt = VT_BSTR
        self.failUnless(v.value in ("", None))

    def test_empty_BSTR(self):
        v = VARIANT()
        v.value = ""
        self.assertEqual(v.vt, VT_BSTR)

    def test_UDT(self):
        from comtypes.gen.TestComServerLib import MYCOLOR
        v = VARIANT(MYCOLOR(red=1.0, green=2.0, blue=3.0))
        value = v.value
        self.failUnlessEqual((1.0, 2.0, 3.0),
                             (value.red, value.green, value.blue))

        def func():
            v = VARIANT(MYCOLOR(red=1.0, green=2.0, blue=3.0))
            return v.value

        bytes = find_memleak(func)
        self.failIf(bytes, "Leaks %d bytes" % bytes)

    def test_ctypes_in_variant(self):
        v = VARIANT()
        objs = [(c_ubyte(3), VT_UI1),
                (c_char("x"), VT_UI1),
                (c_byte(3), VT_I1),
                (c_ushort(3), VT_UI2),
                (c_short(3), VT_I2),
                (c_uint(3), VT_UI4),
                (c_uint64(2**64), VT_UI8),
                (c_int(3), VT_I4),
                (c_int64(2**32), VT_I8),
                (c_double(3.14), VT_R8),
                (c_float(3.14), VT_R4),
                ]
        for value, vt in objs:
            v.value = value
            self.failUnlessEqual(v.vt, vt)

    def test_byref(self):
        variable = c_int(42)
        v = VARIANT(byref(variable))
        self.failUnlessEqual(v[0], 42)
        self.failUnlessEqual(v.vt, VT_BYREF | VT_I4)
        variable.value = 96
        self.failUnlessEqual(v[0], 96)

        variable = c_int(42)
        v = VARIANT(pointer(variable))
        self.failUnlessEqual(v[0], 42)
        self.failUnlessEqual(v.vt, VT_BYREF | VT_I4)
        variable.value = 96
        self.failUnlessEqual(v[0], 96)


class NdArrayTest(unittest.TestCase):
    def test_double(self):
        np = get_numpy()
        if np is None:
            return
        for dtype in ('float32', 'float64'):
            # because of FLOAT rounding errors, whi will only work for
            # certain values!
            a = np.array([1.0, 2.0, 3.0, 4.5], dtype=dtype)
            v = VARIANT()
            v.value = a
            self.failUnless((v.value == a).all())

    def test_int(self):
        np = get_numpy()
        if np is None:
            return
        for dtype in ('int8', 'int16', 'int32', 'int64', 'uint8',
                'uint16', 'uint32', 'uint64'):
            a = np.array((1, 1, 1, 1), dtype=dtype)
            v = VARIANT()
            v.value = a
            self.failUnless((v.value == a).all())

    def test_mixed(self):
        np = get_numpy()
        if np is None:
            return

        now = datetime.datetime.now()
        a = np.array(
            [11, "22", None, True, now, decimal.Decimal("3.14")]).reshape(2,3)
        v = VARIANT()
        v.value = a
        self.failUnless((v.value == a).all())


class ArrayTest(unittest.TestCase):
    def test_double(self):
        import array
        for typecode in "df":
            # because of FLOAT rounding errors, whi will only work for
            # certain values!
            a = array.array(typecode, (1.0, 2.0, 3.0, 4.5))
            v = VARIANT()
            v.value = a
            self.failUnlessEqual(v.value, (1.0, 2.0, 3.0, 4.5))

    def test_int(self):
        import array
        for typecode in "bhiBHIlL":
            a = array.array(typecode, (1, 1, 1, 1))
            v = VARIANT()
            v.value = a
            self.failUnlessEqual(v.value, (1, 1, 1, 1))

################################################################
def run_test(rep, msg, func=None, previous={}, results={}):
##    items = [None] * rep
    if func is None:
        locals = sys._getframe(1).f_locals
        func = eval("lambda: %s" % msg, locals)
    items = xrange(rep)
    from time import clock
    start = clock()
    for i in items:
        func(); func(); func(); func(); func()
    stop = clock()
    duration = (stop-start)*1e6/5/rep
    try:
        prev = previous[msg]
    except KeyError:
        print >> sys.stderr, "%40s: %7.1f us" % (msg, duration)
        delta = 0.0
    else:
        delta = duration / prev * 100.0
        print >> sys.stderr, "%40s: %7.1f us, time = %5.1f%%" % (msg, duration, delta)
    results[msg] = duration
    return delta


def check_perf(rep=20000):
    from ctypes import c_int, byref
    import comtypes.automation
    print (comtypes.automation)
    variable = c_int()
    by_var = byref(variable)
    ptr_var = pointer(variable)

    import cPickle
    try:
        previous = cPickle.load(open("result.pickle", "rb"))
    except IOError:
        previous = {}

    results = {}

    d = 0.0
    d += run_test(rep, "VARIANT()", previous=previous, results=results)
    d += run_test(rep, "VARIANT(by_var)", previous=previous, results=results)
    d += run_test(rep, "VARIANT(ptr_var)", previous=previous, results=results)
    d += run_test(rep, "VARIANT().value", previous=previous, results=results)
    d += run_test(rep, "VARIANT(None).value", previous=previous, results=results)
    d += run_test(rep, "VARIANT(42).value", previous=previous, results=results)
    d += run_test(rep, "VARIANT(42L).value", previous=previous, results=results)
    d += run_test(rep, "VARIANT(3.14).value", previous=previous, results=results)
    d += run_test(rep, "VARIANT(u'Str').value", previous=previous, results=results)
    d += run_test(rep, "VARIANT('Str').value", previous=previous, results=results)
    d += run_test(rep, "VARIANT((42,)).value", previous=previous, results=results)
    d += run_test(rep, "VARIANT([42,]).value", previous=previous, results=results)

    print "Average duration %.1f%%" % (d / 10)
##    cPickle.dump(results, open("result.pickle", "wb"))

if __name__ == '__main__':
    try:
        unittest.main()
    except SystemExit:
        pass
    import comtypes
    print "Running benchmark with comtypes %s/Python %s ..." % (comtypes.__version__, sys.version.split()[0],)
    check_perf()
