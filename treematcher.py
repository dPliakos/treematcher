#system modules
import re
from itertools import permutations

# third party modules
import ast
import six
import copy
from ete3 import PhyloTree, Tree, NCBITaxa
from symbols import SYMBOL, SET

# internal modules
#...

#developement modules
from sys import exit


class TreePatternCache(object):
    def __init__(self, tree):
        """ Creates a cache for attributes that require multiple tree
        traversal when using complex TreePattern queries.

        :param tree: a regular ETE tree instance
         """
        # Initialize cache (add more stuff as needed)
        self.leaves_cache = tree.get_cached_content()
        self.all_node_cache = tree.get_cached_content(leaves_only=False)

    def get_cached_attr(self, attr_name, node, leaves_only=False):
        """
        easy access to cached attributes on trees.

        :param attr_name: any attribute cached in tree nodes (e.g., species,
         name, dist, support, etc.)

        :param node: The pattern tree containing the cache

        :leaves_only: If True, return cached values only from leaves

        :return: cached values for the requested attribute (e.g., Homo sapiens,
         Human, 1.0, etc.)

        """
        #print("USING CACHE")
        cache = self.leaves_cache if leaves_only else self.all_node_cache
        values = [getattr(n, attr_name, None) for n in cache[node]]
        return values

    def get_leaves(self, node):
        return self.leaves_cache[node]

    def get_descendants(self, node):
        return self.all_node_cache[node]


class _FakeCache(object):
    """TreePattern cache emulator."""
    def __init__(self):
        pass

    def get_cached_attr(self, attr_name, node, leaves_only=False):
        """ Helper function to mimic the behaviour of a cache, so functions can
        refer to a cache even when one has not been created, thus simplifying code
        writing. """
        if leaves_only:
            iter_nodes = node.iter_leaves
        else:
            iter_nodes = node.traverse

        values = [getattr(n, attr_name, None) for n in iter_nodes()]
        return values

    def get_leaves(self, node):
        return node.get_leaves()

    def get_descendants(self, node):
        return node.get_descendants()


class PatternSyntax(object):
    def __init__(self):
        # Creates a fake cache to ensure all functions below are functioning
        # event if no real cache is provided
        self.__fake_cache = _FakeCache()
        self.__cache = None

    def __get_cache(self):
        if self.__cache:
            return self.__cache
        else:
            return self.__fake_cache

    def __set_cache(self, value):
        self.__cache = value

    cache = property(__get_cache, __set_cache)

    def leaves(self, target_node):
        return sorted([name for name in self.cache.get_cached_attr(
            'name', target_node, leaves_only=True)])

    def descendants(self, target_node):
        return sorted([name for name in self.cache.get_cached_attr(
            'name', target_node)])

    def species(self, target_node):
        return set([name for name in self.cache.get_cached_attr(
            'species', target_node, leaves_only=True)])

    def contains_species(self, target_node, species_names):
        """
        Shortcut function to find the species at a node and any of it's descendants.
        """
        if isinstance(species_names, six.string_types):
            species_names = set([species_names])
        else:
            species_names = set(species_names)

        found = 0
        for sp in self.cache.get_cached_attr('species', target_node, leaves_only=True):
            if sp in species_names:
                found += 1
        return found == len(species_names)

    def contains_leaves(self, target_node, node_names):
        """ Shortcut function to find if a node contains at least one of the
        node names provided. """

        if isinstance(node_names, six.string_types):
            node_names = set([node_names])
        else:
            node_names = set(node_names)

        found = 0
        for name in self.cache.get_cached_attr('name', target_node, leaves_only=True):
            if name in node_names:
                found += 1
        return found == len(node_names)

    def n_species(self, target_node):
        """ Shortcut function to find the number of species within a node and
        any of it's descendants. """

        species = self.cache.get_cached_attr('species', target_node, leaves_only=True)
        return len(set(species))

    def n_leaves(self, target_node):
        """ Shortcut function to find the number of leaves within a node and any
                of it's descendants. """
        return len(self.cache.get_leaves(target_node))

    def n_duplications(self, target_node):
        """
            Shortcut function to find the number of duplication events at or below a node.
            :param target_node: Node to be evaluated, given as @.
            :return: True if node is a duplication, otherwise False.
        """
        events = self.cache.get_cached_attr('evoltype', target_node)
        return(events.count('D'))

    def n_speciations(self, target_node):
        """
            Shortcut function to find the number of speciation events at or below a node.
        """
        events = self.cache.get_cached_attr('evoltype', target_node)
        return(events.count('S'))


    # TODO: review next function

    def smart_lineage(self, constraint):
        """ Get names instead of tax ids if a string is given before the "in
        @.linage" in a query. Otherwise, returns Taxonomy ids. Function also
        works for constraint that contains something besides the given target
        node (e.g., @.children[0].lineage).

        :param constraint: Internal use.

        :return:  Returns list of lineage tax ids if taxid is searched,
        otherwise returns names in lineage. """

        parsedPattern = ast.parse(constraint, mode='eval')

        lineage_node = [n for n in ast.walk(parsedPattern)
                        if hasattr(n, 'comparators') and type(n.comparators[0]) == ast.Attribute
                        and n.comparators[0].attr == "lineage"]

        index = 0
        for lineage_search in lineage_node:
            if hasattr(lineage_node[index].left,'s'):
                # retrieve what is between __target and .lineage
                found_target = (re.search(r'__target[^ ]*\.lineage', constraint).span())
                extracted_target = constraint[found_target[0]: found_target[1]]

                syntax = "(ncbi.get_taxid_translator(" + \
                         str(extracted_target) + ")).values()"
                if index == 0:
                    constraint = constraint.replace(str(extracted_target), syntax, 1)
                else:

                    constraint = re.sub(r'^((.*?' + extracted_target + r'.*?){' + str(index) + r'})' + extracted_target,
                             r'\1' + syntax, constraint)

            index += 1

        return constraint


class TreePattern(Tree):
    def __str__(self):
        return self.get_ascii(show_internal=True, attributes=["name"])

    def __init__(self, newick=None, format=1, dist=None, support=None,
                 name=None, quoted_node_names=True, syntax=None):
        """ Creates a tree pattern instance that can be used to search within
        other trees.

        :param newick: Path to the file containing the tree or, alternatively,
            the text string containing the same information.
        :param format: subnewick format that is a number between 0 (flexible)
            and 9 (leaf name only), or 100 (topology only).
        :param quoted_node_names: Set to True if node names are quoted with
            stings, otherwise False.
        :syntax: Syntax controller class containing functions to use as
            constraints within the pattern.
        """
        # Load the pattern string as a normal ETE tree, where node names are
        # python expressions
        super(TreePattern, self).__init__(newick, format, dist, support, name, quoted_node_names)

        # Set a default syntax controller if a custom one is not provided
        self.syntax = syntax if syntax else PatternSyntax()

        # check the tree syntax.

    def is_in_bounds(self, bound, test):
        """
        Checks in case of indirect connection the current node is inside the bounds.
        :param bound: specifies what bound to test
        """

        if bound == 'low':
            return test >= self.controller["low"]
        elif bound == 'high':
            if self.controller["high"] >= 0:
                # high bound has to be less but not equal, because it performs a 'can skip one more' test.
                return test <= self.controller["high"]
        return True

    def find_extreme_case(self, match_list):
        """
        Given a single match pattern and a list of (matched) nodes
        returns the one that fulfills the constraint. That constraint should
        describe an axtreme condition such as minimum or maxhimum.

        :param match_list: a list of (matched) nodes
        """

        # find the node in self that has the comparison expression.
        # now is useless. In case this comparison can be made inside other
        # patterns, the every pattern should compare their corresponding node of
        # the other patterns.
        for node in self.traverse():
            if node.controller["single_match"]:
                pattern = node
                constraint = pattern.controller["single_match_contstraint"]

        # for all nodes in the matched pattern find the one that fits the best
        # the constraint expression.
        # assumes that the root has to be tested.
        correct_node = match_list[0]

        st = False # truth flag for eval()

        for node in match_list:
            # for every node in the list compare the best match so far with
            # the current node in the list priority.
            constraint = pattern.controller["single_match_contstraint"]
            constraint_scope = {attr_name: getattr(self.syntax, attr_name)
                                for attr_name in dir(self.syntax)}
            constraint_scope.update({"__target_node": node})
            constraint_scope.update({"__correct_node": correct_node})
            constraint = constraint.replace("@", "__target_node")
            constraint = constraint.replace(SET["all_nodes"], "__correct_node")

            try:
                st = eval(constraint, constraint_scope)

            except ValueError:
                raise ValueError("not a boolean result: . Check quoted_node_names.")

            except (AttributeError, IndexError) as err:
                raise ValueError('Constraint evaluation failed at %s: %s' %
                                 (target_node, err))
            except NameError:
                try:
                    # temporary fix. Can not access custom syntax on all nodes. Get it from the root node.
                    root_syntax = self.get_tree_root().syntax
                    constraint_scope = {attr_name: getattr(root_syntax, attr_name)
                                        for attr_name in dir(root_syntax)}
                    constraint_scope.update({"__target_node": node})
                    constraint_scope.update({"__correct_node": correct_node})

                    st = eval(constraint, constraint_scope)
                    if st: correct_node = node

                except NameError as err:
                    raise NameError('Constraint evaluation failed at %s: %s' %
                             (target_node, err))
            else:
                if st: correct_node = node
        return correct_node

    def decode_repeat_symbol(self, bounds):
        """
        Extracts valuable information from the controlled skipping case.

        :param bounds: a string that contains the {x-y} pattern.

        returns a list with the lower and the highest bounds in respectively order.
        """
        bounds = bounds[1:len(bounds)-1]
        if '-' in bounds:
            split = bounds.split("-")
            low = int(split[0]) if split[0] else 0
            high = int(split[1] ) if split[1] else -1
        else:
            low = high = int(bounds)
        return [low, high]

    def parse_metacharacters(self):
        """
        Takes a string as node name and extracts the metacharacters.
        Assumes that all metacharacters are defined at the end of the string.
        returns a list containing all metacharacters in the string.
        """
        metacharacters = []

        while len(self.name) > 0 and  self.name[len(self.name)-1] in SYMBOL.values():

            if SYMBOL["defined_number_set_start"] in self.name:
                metacharacters += [
                self.name [
                self.name.find(SYMBOL["defined_number_set_start"]):self.name.find(SYMBOL["defined_number_set_end"]) + 1
                ]]
                self.name = self.name[0:self.name.find(SYMBOL["defined_number_set_start"])]
            else:
                metacharacters += [ self.name[len(self.name) - 1] ]

                if len(self.name) > 0:
                    self.name = self.name[0:len(self.name)-1]

        if len(self.name) < 1:
            self.name = SYMBOL["node_reference"]
        return metacharacters

    def parse_node_name(self):
        """
        transforms TreePattern.name attribute to a python expression.
        Assumes expressions use commas to describe different attributes.
        """
        expressions = [ exp.strip() for exp in self.name.split(",") ]

        for i in range(0, len(expressions)):
            # len(expressions[i]) > 0 prevents @.name == "" case
            if len(expressions[i]) > 0 and all(letter.isalpha() for letter in expressions[i]):
                expressions[i] = '@.name == "' + expressions[i] + '"'

        # prevents the " _expressions_ ... and  __empty_exp__ " case
        return " and ".join(exp for exp in expressions if len(exp) > 0)

    def define_skipping_properties(self, metacharacters):
        controller = {}

        for metacharacter in metacharacters:

            # update controller in case of root or leaf metacharacters and set the node name
            if metacharacter == SYMBOL["is_root"]:
                controller["root"] = True
            if metacharacter == SYMBOL["is_leaf"]:
                controller["leaf"] = True
            if metacharacter == SYMBOL["not"]:
                controller["not"] = True

            # update controller according to metacharacter connection properties.
            if metacharacter == SYMBOL["one_or_more"]:
                controller["allow_indirect_connection"] = True
                controller["direct_connection_first"] = False
                controller["low"] = 1
            elif metacharacter == SYMBOL["zero_or_more"]:
                controller["allow_indirect_connection"] = True
                controller["direct_connection_first"] = True
            elif metacharacter == SYMBOL["zero_or_one"]:
                controller["direct_connection_first"] = True
                controller["allow_indirect_connection"] = True
                controller["high"] = 1
            elif SYMBOL["defined_number_set_start"] in metacharacter:
                split = self.name.split(SYMBOL["defined_number_set_start"])
                bounds = self.decode_repeat_symbol(metacharacter)
                controller["low"] = bounds[0]
                controller["high"] = bounds[1]
                controller["allow_indirect_connection"] = True
                if controller["low"]  == 0: controller["direct_connection_first"] = True
                else: controller["direct_connection_first"] = False

        return controller

    def set_controller(self):
        """
        Creates a dictionary that contains information about a node.
        That information is about how a node interacts with the tree topology.
        It describes how the metacharacter connects with the rest of nodes and
        if it is leaf or root.
        """
        controller = {}

        metacharacters = []
        if len(self.name) > 0:
            metacharacters = self.parse_metacharacters()

        # bounds, (already) skipped nodes values and connection properties.
        controller["not"] = False
        controller["low"] = 0
        controller["high"] = -1
        controller["skipped"] = 0
        controller["single_match"] = False
        controller["allow_indirect_connection"] = False
        controller["direct_connection_first"] = False

        properties = self.define_skipping_properties(metacharacters)
        controller.update(properties)

        # transform node name to python expression
        self.name = self.parse_node_name()

        # review scope
        # transform sets to the corresponding code
        if SET["any_child"] in self.name:
            self.name = " any( " + self.name.split("[")[0] + " " + ("[" + self.name.split("[")[1]).replace(SET["any_child"], "x") + " for x in __target_node.children)"
        if SET["children"] in self.name:
            self.name = " all( " + self.name.split("[")[0] + " " + ("[" + self.name.split("[")[1]).replace(SET["children"], "x") + " for x in __target_node.children)"
        if SET["all_nodes"] in self.name:
            controller["single_match"] = True
            controller["single_match_contstraint"] = self.name
            self.name = '@'

        self.controller = controller
        return self.controller["single_match"]

    # FUNCTIONS EXPOSED TO USERS START HERE
    def match(self, node, cache=None):
        """
        Check all constraints interactively on the target node.

        :param node: A tree (node) to be searched for a given pattern.

        :param local_vars:  Dictionary of TreePattern class variables and
        functions for constraint evaluation.

        :return: True if a match has been found, otherwise False.
        """
        self.syntax.cache = cache
        # does the target node match the root node of the pattern?

        #check the zero intermediate node case.
        #assumes that SYMBOL["zero_or_more"] has only one child.
        if self.controller["direct_connection_first"] and not self.is_leaf():
            self = self.children[0]

        status = self.is_local_match(node, cache)

        if not self.is_leaf and self.controller["not"]:
            status = not status

        if not status:
            if self.controller["allow_indirect_connection"] and self.is_leaf():
                pass
            elif self.up is not None and self.up.controller["allow_indirect_connection"] and self.up.is_in_bounds("high", self.up.controller["skipped"] + 1 ):  # skip node by resetting pattern
                status = True
                self = self.up
                self.controller["skipped"] += 1
        elif self.controller["allow_indirect_connection"] and self.controller["skipped"] == 0:
            self.controller["skipped"] += 1


        # if so, continues evaluating children pattern nodes against target node
        # children
        if status and self.children:

                #if the number of children do not match, find where they do and check that
                nodes = []

                if len(node.children) < len(self.children):
                    if self.controller["allow_indirect_connection"]:
                        count = 0
                        for skip_to_node in node.traverse(strategy="levelorder"):
                            # skip to node with correct number of children
                            if len(skip_to_node.children) >= len(self.children):
                                count += 1
                                nodes += [skip_to_node]
                                sisters = skip_to_node.get_sisters()
                                if len(sisters) > 0:
                                   for sister in sisters:
                                       nodes += [sister]

                                break
                        if count < 1:
                            status = False

                    else:
                        #print("setting status to false")
                        status = False

                # If pattern node expects children nodes, tries to find a
                # combination of target node children that match the pattern

                if len(nodes) == 0:
                    nodes = [node]

                for node in nodes:
                    sub_status_count = 0
                    if len(node.children) >= len(self.children):
                        test_children_properties = False
                        continious_matched = []
                        for candidate in permutations(node.children):
                            sub_status = True
                            current_matched = 0

                            i = 0
                            j = 0
                            while i < len(self.children):
                                st = self.children[i].match(candidate[j], cache)

                                #print "testing: " + self.children[i].name + " -- " + candidate[j].name + " -- st: " + str(st) + " -- subst: " + str(sub_status)

                                if self.children[i].is_leaf() and (self.children[i].controller["allow_indirect_connection"] or self.children[i].controller["not"]) and sub_status: # REVIEW ME
                                    test_children_properties = True
                                    if st:
                                        current_matched += 1
                                    j += 1
                                    if j < len(candidate):
                                        continue
                                    else:
                                        #print "updating " + str(current_matched) + " to " + str(continious_matched)
                                        if current_matched > 0: continious_matched += [current_matched]
                                        current_matched = 0
                                else :
                                    if st and not self.is_in_bounds("low", self.controller["skipped"]):
                                        # in case it matches, but has exited the lower bound (in case it exist), force False the match
                                        st = False
                                    if st == False and self.controller["allow_indirect_connection"] and len(candidate[i].children) > 0:
                                        pass
                                    else:
                                        sub_status &= st
                                        if sub_status: sub_status_count += 1
                                i += 1
                                j += 1

                            if test_children_properties:
                                continue
                            elif sub_status and sub_status_count > 0:
                                status = True
                                break
                            else:
                                status = False
                        if test_children_properties:
                            sub_sub_status = False
                            #print continious_matched
                            if len(continious_matched) > 0 :
                                for con_matches in continious_matched:
                                    low_test = self.children[-1].is_in_bounds("low", con_matches)
                                    high_test = self.children[-1].is_in_bounds("high", con_matches)
                                    sub_sub_status |= low_test and high_test
                                    #sub_sub_status = not sub_sub_status
                                sub_status = sub_sub_status
                            #print "exited with sub_sub_status: " + str(sub_status)
                            #if not self.children[-1].controller["direct_connection_first"]:
                            elif self.children[-1].controller["direct_connection_first"]:
                                sub_sub_status = True
                            if self.children[-1].controller["not"]:
                                print "not case"
                                sub_sub_status = not sub_sub_status
                            sub_status = sub_sub_status
                            status = sub_status
                            if sub_status: sub_status_count += 1

                    if status and sub_status_count > 0:
                        break

        # 'skipped' tracks the maximum skipped node. So only in case of not match, it decreases
        if not status and self.controller["allow_indirect_connection"]: self.controller["skipped"] -= 1
        return status


    def is_local_match(self, target_node, cache):
        """ Evaluate if this pattern constraint node matches a target tree node.

        TODO: args doc here...
        """

        # Creates a local scope containing function names, variables and other
        # stuff referred within the pattern expressions. We use Syntax() as a
        # container of those custom functions and shortcuts.

        constraint_scope = {attr_name: getattr(self.syntax, attr_name)
                            for attr_name in dir(self.syntax)}
        constraint_scope.update({"__target_node": target_node})
        constraints = []

        if "root" in self.controller and self.controller["root"]: constraints.append("__target_node.is_root()")
        if "leaf" in self.controller and self.controller["leaf"]: constraints.append("__target_node.is_leaf()")


        if not self.name:
            # empty pattern node should match any target node
            constraints.append('')
        elif '@' in self.name:
            # use as any node if used alone or
            # converts references to node itself if it's in an expression.
            if len(self.name) == 1: constraints.append('')
            else: constraints.append(self.name.replace('@', '__target_node'))
        elif self.controller["allow_indirect_connection"]:
            # pattern nodes that allow indirect connection should match any target node
            constraints.append('')

        else:
            # if no references to itself, let's assume we search an exact name
            # match (allows using regular newick string as patterns)
            constraints.append('__target_node.name == "%s"' % self.name)

        try:
            st = True
            for constraint in constraints:
                if constraint:
                    st &= eval(constraint, constraint_scope)
                else: st &= True

        except ValueError:
            raise ValueError("not a boolean result: . Check quoted_node_names.")

        except (AttributeError, IndexError) as err:
            raise ValueError('Constraint evaluation failed at %s: %s' %
                             (target_node, err))
        except NameError:
            try:
                # temporary fix. Can not access custom syntax on all nodes. Get it from the root node.
                root_syntax = self.get_tree_root().syntax
                constraint_scope = {attr_name: getattr(root_syntax, attr_name)
                                    for attr_name in dir(root_syntax)}
                constraint_scope.update({"__target_node": target_node})

                st = True
                for constraint in constraints:
                    if constraint:
                        st &= eval(constraint, constraint_scope)
                    else: st &= True
                return st
            except NameError as err:
                raise NameError('Constraint evaluation failed at %s: %s' %
                         (target_node, err))
        else:
            return st


    def find_match(self, tree, maxhits=1, cache=None, target_traversal="preorder"):
        """ A pattern search continues until the number of specified matches are
        found.
        :param tree: tree to be searched for a matching pattern.
        :param maxhits: Number of matches to be searched for.
        :param cache: When a cache is provided, preloads target tree information
                               (recommended only for large trees)
        :param None maxhits: Pattern search will continue until all matches are found.
        :param target_traversal: choose the traversal order (e.g. preorder, levelorder, etc)
        :param nested: for each match returned,

        """

        # the controller is for only one use, because it changes the node names.
        # for that reason a deepcopy of the pattern and not the pattern
        # is traversed. Very slow operation.
        one_use_pattern = copy.deepcopy(self)

        # indicaes whether the pattern is a pattern of single match
        # such as maximum or minimum value of an attribute
        single_match_pattern = False

        # sets the controller for every node.
        # should chagne if only is a metacharacter acording to benchmarking tests.
        # if one node indicates single_match, the whole pattern is single_match.
        # no functionality to support other than pattern's root single_match yet
        for node in one_use_pattern.traverse():
            single_match_pattern |= node.set_controller()

        # in case of single_match pattern save the nodes and filter them
        # in other case find the requested match
        if single_match_pattern:
            matched_nodes = []
            for node in tree.traverse(target_traversal):
                if one_use_pattern.match(node, cache):
                    matched_nodes += [node]
            yield one_use_pattern.find_extreme_case(matched_nodes)
        else:
            num_hits = 0
            for node in tree.traverse(target_traversal):
                if one_use_pattern.match(node, cache):
                    num_hits += 1
                    yield node
                if maxhits is not None and num_hits >= maxhits:
                    break


def test():
    print "compiled.\nrun /test/test_metacharacters.py and /test/test_logical_comparison.py to test."
    t3 = PhyloTree(""" ((c, d, e, f)b)a ; """, format=8, quoted_node_names=False)

    (t3&'c').dist = 0.5
    (t3&'e').dist = 0.5
    (t3&'f').dist = 0.5

    pattern1 = TreePattern(""" (('d!', '@.dist > 0.4')'b')'a, ^' ;""", quoted_node_names=True)
    print len(list(pattern1.find_match(t3))) > 0

if __name__ == '__main__':
    test()
