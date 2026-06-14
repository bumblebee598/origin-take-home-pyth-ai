from manim import *


class Showcase(Scene):
    """A tour of the core ManimCE building blocks:
    Scene -> mobjects -> animations, plus positioning, graphs, and updaters.
    Render with:  manim -pql showcase.py Showcase
    """

    def construct(self):
        # 1. TEXT + a static add() (no animation) ----------------------------
        title = Text("Manim, in one scene", weight=BOLD).scale(0.9)
        self.play(Write(title))           # Write = draw text stroke-by-stroke
        self.wait(0.5)
        self.play(title.animate.to_edge(UP))  # .animate = animate any method call

        # 2. SHAPES + styling + relative positioning ------------------------
        circle = Circle(radius=1).set_fill(BLUE, opacity=0.6).set_stroke(WHITE)
        square = Square(side_length=2).set_fill(GREEN, opacity=0.6)
        square.next_to(circle, RIGHT, buff=1)   # place square relative to circle

        self.play(Create(circle))         # Create = trace the outline
        self.play(FadeIn(square, shift=UP))   # FadeIn with a directional shift
        self.wait(0.5)

        # 3. TRANSFORM one mobject into another -----------------------------
        self.play(Transform(circle, Triangle().set_fill(RED, opacity=0.6)
                            .move_to(circle)))
        self.wait(0.5)

        # 4. .animate chaining: shift + rotate + scale at once --------------
        self.play(square.animate.rotate(PI / 4).scale(0.7).shift(LEFT * 0.5))
        self.wait(0.5)

        # 5. Clear the stage, then build a GRAPH (the core of explainers) ----
        self.play(FadeOut(circle), FadeOut(square))

        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-1, 9, 2],
            axis_config={"include_tip": True},
        ).scale(0.8).to_edge(DOWN, buff=0.6)
        axis_labels = VGroup(
            Text("x").scale(0.5).next_to(axes.x_axis, RIGHT),
            Text("f(x)").scale(0.5).next_to(axes.y_axis, UP),
        )

        graph = axes.plot(lambda x: x**2, x_range=[-3, 3], color=YELLOW)
        graph_label = Text("f(x) = x squared").scale(0.5).next_to(graph, UR, buff=0.1)

        self.play(Create(axes), Write(axis_labels))
        self.play(Create(graph), Write(graph_label))
        self.wait(0.5)

        # 6. UPDATERS: a dot that rides the curve, label tracks it ----------
        t = ValueTracker(-3)
        dot = always_redraw(
            lambda: Dot(axes.c2p(t.get_value(), t.get_value() ** 2), color=RED)
        )
        readout = always_redraw(
            lambda: Text(f"x = {t.get_value():.1f}").scale(0.5).to_corner(UR)
        )
        self.add(dot, readout)
        self.play(t.animate.set_value(3), run_time=3, rate_func=smooth)
        self.wait(1)