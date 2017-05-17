import unittest

#assuming ete3 is not installed. they will be imported from local directory on developement modules.
from ete3 import PhyloTree, Tree, NCBITaxa
from treematcher import TreePattern


# plus symbol acts "one_or_more" matches
# trees from treematcher.py test function, except t6.

class Test_one_or_more_functionality_test(unittest.TestCase):
    def setUp(self):
        self.t1 = PhyloTree(""" ((c,g)a) ; """, format=8, quoted_node_names=False)
        self.t2 = PhyloTree(""" ((c,d)a) ; """, format=8, quoted_node_names=False)
        self.t3 = PhyloTree(""" ((d,c)b)a ; """, format=8, quoted_node_names=False)
        self.t4 = PhyloTree(""" ((c,d),(e,f)b)a ; """, format=8, quoted_node_names=False)
        self.t5 = PhyloTree(""" (((e,f)dum,(c,d)dee)b)a ; """, format=8, quoted_node_names=False)
        self.t6 = PhyloTree(""" ((d,c)a)a ; """, format=8, quoted_node_names=False)
        self.t11 = PhyloTree("""  ( ((e, f, g) c) b, ((g, h, i)c) d) a ; """, format=8, quoted_node_names=False)
        self.t12 = PhyloTree("""  ((( ((e, f, g) c) b, (((g, h, i)c)n) d)k)m) a ; """, format=8, quoted_node_names=False)

        self.pattern = TreePattern(""" ((c)+)a ;""", quoted_node_names=False)

    # there is no intermediate node between 'c' and 'a' nodes.
    def test_no_match(self):
        result = len(list(self.pattern.find_match(self.t1)))
        self.assertTrue(result == 0)

    # there is one intermediate node
    def test_one_intermediate_node(self):
        result = len(list(self.pattern.find_match(self.t3)))
        self.assertTrue(result > 0)

    #one intermediate node. pattern's 'c' (lowest node) has siter
    def test_one_intermediate_node_with_sister(self):
        result = len(list(self.pattern.find_match(self.t4)))
        self.assertTrue(result > 0)

    # two intermediate nodes. check the 'more' functionality
    def test_two_intermediate_nodes(self):
        result = len(list(self.pattern.find_match(self.t5)))
        self.assertTrue(result > 0)

    # one intermediate node. same name as the match.
    def test_one_intermediate_node_with_the_same_name(self):
        result = len(list(self.pattern.find_match(self.t6)))
        self.assertTrue(result == 1)

    # one intermediate node. intermediate node has siter node
    def test_one_intermediate_node_more_complex_tree(self):
        result = len(list(self.pattern.find_match(self.t11)))
        self.assertTrue(result > 0)

    # four intermediate nodes.
    def test_four_intermediate_nodes(self):
        result = len(list(self.pattern.find_match(self.t12)))
        self.assertTrue(result > 0)


class reference_as_any_node_funcitonality_test(unittest.TestCase):
    def setUp(self):
        self.t1 = PhyloTree(""" ((c,g)a) ; """, format=8, quoted_node_names=False)
        self.t2 = PhyloTree(""" ((c,d)a) ; """, format=8, quoted_node_names=False)
        self.t3 = PhyloTree(""" ((d,c)b)a ; """, format=8, quoted_node_names=False)
        self.t4 = PhyloTree(""" ((c,d),(e,f)b)a ; """, format=8, quoted_node_names=False)
        self.t5 = PhyloTree(""" (((e,f)dum,(c,d)dee)b)a ; """, format=8, quoted_node_names=False)
        self.t6 = PhyloTree(""" ((d,c)a)a ; """, format=8, quoted_node_names=False)
        self.t11 = PhyloTree("""  ( ((e, f, g) c) b, ((g, h, i)c) d) a ; """, format=8, quoted_node_names=False)
        self.t12 = PhyloTree("""  ((( ((e, f, g) c) b, (((g, h, i)c)n) d)k)m) a ; """, format=8, quoted_node_names=False)

        self.pattern = TreePattern(""" ((c)@)a ;""", quoted_node_names=False)

    # there is no intermediate node between 'c' and 'a' nodes.
    def test_no_match(self):
        result = len(list(self.pattern.find_match(self.t1)))
        self.assertTrue(result == 0)

    # there is one intermediate node
    def test_one_intermediate_node(self):
        result = len(list(self.pattern.find_match(self.t3)))
        self.assertTrue(result > 0)

    #one intermediate node. pattern's 'c' (lowest node) has siter
    def test_one_intermediate_node_with_sister(self):
        result = len(list(self.pattern.find_match(self.t4)))
        self.assertTrue(result > 0)

    # two intermediate nodes. check the 'more' functionality
    def test_two_intermediate_nodes(self):
        result = len(list(self.pattern.find_match(self.t5)))
        self.assertTrue(result == 0)

    def test_one_intermediate_node_with_the_same_name(self):
        result = len(list(self.pattern.find_match(self.t6)))
        self.assertTrue(result > 0)

    # one intermediate node. intermediate node has siter node
    def test_one_intermediate_node_more_complex_tree(self):
        result = len(list(self.pattern.find_match(self.t11)))
        self.assertTrue(result > 0)

    # four intermediate nodes.
    def test_four_intermediate_nodes(self):
        result = len(list(self.pattern.find_match(self.t12)))
        self.assertTrue(result == 0)

class Test_zero_or_more_functionality_test(unittest.TestCase):
    def setUp(self):
        self.t1 = PhyloTree(""" ((c,g)a) ; """, format=8, quoted_node_names=False)
        self.t2 = PhyloTree(""" ((c,d)a) ; """, format=8, quoted_node_names=False)
        self.t3 = PhyloTree(""" ((d,c)b)a ; """, format=8, quoted_node_names=False)
        self.t4 = PhyloTree(""" ((c,d),(e,f)b)a ; """, format=8, quoted_node_names=False)
        self.t5 = PhyloTree(""" (((e,f)dum,(c,d)dee)b)a ; """, format=8, quoted_node_names=False)
        self.t6 = PhyloTree(""" ((d,c)a)a ; """, format=8, quoted_node_names=False)
        self.t11 = PhyloTree("""  ( ((e, f, g) c) b, ((g, h, i)c) d) a ; """, format=8, quoted_node_names=False)
        self.t12 = PhyloTree("""  ((( ((e, f, g) c) b, (((g, h, i)c)n) d)k)m) a ; """, format=8, quoted_node_names=False)
        self.t13 = PhyloTree("""  ( ((e, f, g) c) b, ((g, (w)h, i)c) d) a ; """, format=8, quoted_node_names=False)

        self.pattern  = TreePattern(""" ((c)*)a ;""", quoted_node_names=False)
        self.pattern2  = TreePattern(""" (((d)c)*)a ;""", quoted_node_names=False)
        self.pattern3 = TreePattern(""" ((((w)*)c)*)a ;""", quoted_node_names=False)

    # there is no intermediate node between 'c' and 'a' nodes.
    def test_no_match(self):
        result = len(list(self.pattern.find_match(self.t1)))
        self.assertTrue(result > 0)

    # there is one intermediate node
    def test_one_intermediate_node(self):
        result = len(list(self.pattern.find_match(self.t3)))
        self.assertTrue(result > 0)

    #one intermediate node. pattern's 'c' (lowest node) has siter
    def test_one_intermediate_node_with_sister(self):
        result = len(list(self.pattern.find_match(self.t4)))
        self.assertTrue(result > 0)

    # two intermediate nodes. check the 'more' functionality
    def test_two_intermediate_nodes(self):
        result = len(list(self.pattern.find_match(self.t5)))
        self.assertTrue(result > 0)

    # one intermediate node. same name as the match.
    def test_one_intermediate_node_with_the_same_name(self):
        result = len(list(self.pattern.find_match(self.t6, maxhits=None)))
        self.assertTrue(result == 2)

    # one intermediate node. intermediate node has siter node
    def test_one_intermediate_node_more_complex_tree(self):
        result = len(list(self.pattern.find_match(self.t11)))
        self.assertTrue(result > 0)

    # four intermediate nodes.
    def test_four_intermediate_nodes(self):
        result = len(list(self.pattern.find_match(self.t12)))
        self.assertTrue(result > 0)

    def test_no_result(self):
        result = len(list(self.pattern2.find_match(self.t1)))
        self.assertTrue(result  == 0)

    def test_double_symbols(self):
        result = len(list(self.pattern3.find_match(self.t13)))
        self.assertTrue(result  > 0)


if __name__ == '__main__':
    unittest.main()
