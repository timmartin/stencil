import unittest
import unittest.mock
import ast
import io

from stencil.parser import parse_expression, IfNode, ForNode, ExtendsNode
from stencil.compiler import Parser
from stencil.code_generation import (Literal, Sequence, IfBlock,
                                     ForBlock, ExtendsBlock, ReplaceableBlock,
                                     Execution)


class ParserTest(unittest.TestCase):
    def test_simple_sequence(self):
        parser = Parser()

        sequence = parser.parse([Literal("Foo"),
                                 Literal("Bar")])

        self.assertEqual(2, len(sequence.elements))

    def test_parse_if_block(self):
        parser = Parser()

        sequence = parser.parse([Literal("Foo"),
                                 Execution("if True"),
                                 Literal("Bar"),
                                 Execution("endif"),
                                 Literal("Baz")])

        self.assertEqual(sequence.elements[0],
                         Literal("Foo"))

        self.assertIsInstance(sequence.elements[1],
                              IfBlock)
        # TODO There doesn't seem to be an easy way to verify the
        # contents of the AST object.
        self.assertEqual(sequence.elements[1].sequence.elements[0],
                         Literal("Bar"))

        self.assertEqual(sequence.elements[2],
                         Literal("Baz"))

    def test_parse_for_loop(self):
        parser = Parser()

        sequence = parser.parse([Execution("for x in things"),
                                 Literal("bar"),
                                 Execution("endfor")])

        expected_sequence = Sequence()
        block = ForBlock(ForNode('x', 'things'))
        block.sequence.add_element(Literal("bar"))
        expected_sequence.add_element(block)

        self.assertEqual(sequence.elements,
                         expected_sequence.elements)

    def test_parse_nested(self):
        parser = Parser()

        sequence = parser.parse([Execution("for x in things"),
                                 Execution("if x % 2"),
                                 Execution("endif"),
                                 Execution("endfor")])

        self.assertEqual(1,
                         len(sequence.elements))
        self.assertIsInstance(sequence.elements[0],
                              ForBlock)

        self.assertIsInstance(sequence.elements[0].sequence.elements[0],
                              IfBlock)
        self.assertEqual(1,
                         len(sequence.elements[0].sequence.elements))

    def test_expression_parser(self):
        """Test the expression parser used within the {% %} node"""

        node = parse_expression(["if", "True"])
        self.assertIsInstance(node, IfNode)
        self.assertEqual(node.expression.body.value,
                         True)

        node = parse_expression(["for", "var", "in", "collection"])
        self.assertIsInstance(node, ForNode)
        self.assertEqual(node, ForNode("var", "collection"))

        node = parse_expression(["if", "x", "<", "y"])
        self.assertIsInstance(node, IfNode)
        self.assertEqual(ast.dump(node.expression),
                         "Expression(body=Compare("
                         "left=Name(id='x', ctx=Load()), ops=[Lt()],"
                         " comparators=[Name(id='y', ctx=Load())]))")

        node = parse_expression(["extends", '"other.html"'])
        self.assertIsInstance(node, ExtendsNode)
        self.assertEqual(node.template_name,
                         "other.html")

    def test_extends(self):
        template_locator = unittest.mock.MagicMock()
        template_locator.find_template.return_value = "/wherever/other.html"

        mock_file = io.StringIO("")

        mock_open = unittest.mock.MagicMock(return_value=mock_file)

        with unittest.mock.patch('builtins.open', mock_open):
            parser = Parser(template_locator)

            sequence = parser.parse([Execution('extends "other.html"'),
                                     Execution("block title"),
                                     Literal("My template"),
                                     Execution("endblock")])

        self.assertEqual(1,
                         len(sequence.elements))
        self.assertIsInstance(sequence.elements[0],
                              ExtendsBlock)

        # The template extends an empty template, so the inner
        # template of the extends node is a single empty literal node.
        self.assertEqual([Literal('')],
                         sequence.elements[0].template.elements)

        self.assertEqual(1,
                         len(sequence.elements[0].sequence.elements))
        self.assertIsInstance(sequence.elements[0].sequence.elements[0],
                              ReplaceableBlock)


if __name__ == '__main__':
    unittest.main()
