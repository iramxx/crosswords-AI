import sys

from crossword import *
from queue import Queue
from collections import deque

class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for v in (self.crossword).variables:
            tempset = self.domains[v].copy()
            for word in tempset:
                if len(word) != v.length:
                    self.domains[v].remove(word)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        check_mod_done_on_x = False
        to_remove = set()
        if self.crossword.overlaps[x, y] == None:
            return False
        for word in self.domains[x]:
            i, j = self.crossword.overlaps[x, y]
            check_letter = False
            for correspondant in self.domains[y]:
                if word[i] == correspondant[j]:
                    check_letter = True
                    break
            if check_letter == False:
                check_mod_done_on_x = True
                to_remove.add(word)  

        self.domains[x] -= to_remove      
        return check_mod_done_on_x


    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if arcs is None:
            aarcs = []
            for pair, overlap in self.crossword.overlaps.items():
                if overlap is not None:
                    aarcs.append(pair)
        else:
            aarcs = arcs

        q = deque()
        copy_q = set()

        for arc in aarcs:
            q.append(arc)
            copy_q.add(arc)

        while q:
            curr = q.popleft()
            copy_q.remove(curr)
            X, Y = curr
            check_if_modified = self.revise(X, Y)
            if check_if_modified:
                if len(self.domains[X]) == 0:
                    return False
                for temp in aarcs:
                    if temp in copy_q:
                        continue
                    if temp[1] == X:
                        q.append(temp)
                        copy_q.add(temp)

        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        allvariables = self.crossword.variables
        for var in allvariables:
            if not var in assignment:
                return False
        return True
    
    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        #All values are distinct
        if (len(set(assignment.values()))) < len(assignment.values()):
            return False
        #correct length

        for key in assignment:
            if len(assignment[key]) != key.length:
                return False
        
        #no conflict

        for var1 in assignment:
            for var2 in self.crossword.neighbors(var1):
                if var2 not in assignment:
                    continue
                overlap = self.crossword.overlaps.get((var1, var2))
                if overlap is None:
                    continue
                i, j = overlap
                word1 = assignment[var1]
                word2 = assignment[var2]
                if word1[i] != word2[j]:
                    return False

        return True
        

        

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        neighbors = self.crossword.neighbors(var)
        out = {}

        for word in self.domains[var]:
            out[word] = 0
            for n in neighbors:
                i, j = self.crossword.overlaps.get((var, n))
                if n in assignment:
                    continue
                for word2 in self.domains[n]:
                    if word[i] != word2[j]:
                        out[word] += 1
        
        sorted_keys = sorted(out, key = lambda k: out[k])

        return sorted_keys

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        unassigned = {v for v in self.crossword.variables if v not in assignment}


        num_vars = {}
        for var in unassigned:
            size = len(self.domains[var])
            if size not in num_vars:
                num_vars[size] = set()
            num_vars[size].add(var)
        
        nums_vars_sorted_domain_size = dict(sorted(num_vars.items()))

        key1 = next(iter(nums_vars_sorted_domain_size))
        if len(nums_vars_sorted_domain_size[key1]) == 1:
            return next(iter(nums_vars_sorted_domain_size[key1]))
        else:
            maxsize = -1
            for s in nums_vars_sorted_domain_size[key1]:
                if len(self.crossword.neighbors(s)) > maxsize:
                    maxsize = len(self.crossword.neighbors(s))
                    totake = s
            
            return totake


    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """

        if self.assignment_complete(assignment):
            return assignment

        var = self.select_unassigned_variable(assignment)

        for value in self.order_domain_values(var, assignment):
            new_assignment = assignment.copy()
            new_assignment[var] = value

            if self.consistent(new_assignment):
                result = self.backtrack(new_assignment)
                if result is not None:
                    return result

        return None


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
