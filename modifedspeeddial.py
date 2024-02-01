from __future__ import annotations

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import (
    ColorProperty, VariableListProperty,
    OptionProperty, NumericProperty,
    ObjectProperty, DictProperty,
    BooleanProperty, BoundedNumericProperty, StringProperty
)
from kivy.uix.widget import Widget
from kivymd.theming import ThemableBehavior
from kivymd.uix.behaviors import DeclarativeBehavior
from kivymd.uix.button.button import MDFloatingBottomButton, MDFloatingLabel


class ModifiedSpeedDial(DeclarativeBehavior, ThemableBehavior, Widget):
    """ModifiedSpeedDial: Modified version of :class:`kivymd.uix.button.MDFloatingActionButtonSpeedDial`

 Changes:
- it can be added as a child widget of a button instead of separate widget
- buttons position will be relative to parent button position instead of fixated to right bottom corner of the window
- background width (hint_animation) which depends on longest text makes small hint texts look bad which is fixed now

 Additional options:
- change side of buttons using ``stack_button_direction``
- change side of labels using ``label_direction``
- change distance between button and hint text using ``button_text_offset``
- the widgets will be closed if user clicks outside of the widgets (can be disabled by auto_dismiss=False)
    """

    # Labels
    label_text_color = ColorProperty(None)
    label_bg_color = ColorProperty([0, 0, 0, 0])
    label_radius = VariableListProperty([0], length=4)
    label_direction = OptionProperty("right", options=["left", "right"])
    button_text_offset = NumericProperty(dp(33))

    # Stack Buttons
    bg_color_stack_button = ColorProperty(None)
    color_icon_stack_button = ColorProperty(None)
    bg_hint_color = ColorProperty(None)
    stack_button_direction = OptionProperty("top", options=["top", "bottom"])

    # Animation
    hint_animation = BooleanProperty(False)
    opening_transition = StringProperty("out_cubic")
    closing_transition = StringProperty("out_cubic")
    opening_transition_button_rotation = StringProperty("out_cubic")
    closing_transition_button_rotation = StringProperty("out_cubic")
    opening_time = NumericProperty(0.5)
    closing_time = NumericProperty(0.2)
    opening_time_button_rotation = NumericProperty(0.2)
    closing_time_button_rotation = NumericProperty(0.2)

    # Info
    data = DictProperty()
    auto_dismiss = BooleanProperty(True)
    state = OptionProperty("close", options=("close", "open"))

    # Class Variables
    _anim_buttons_data = {}
    _anim_labels_data = {}
    _direction_vals = {'right': 1, 'top': 1,
                       'left': -1, 'bottom': -1}
    _window = None
    _touch_started_inside = None
    _root_button = type('null', (), {'x': 0, 'y': 0, 'pos': (0, 0), 
                                     'center_x': 0, 'center_y': 0, 
                                     'center': (0, 0), 'right': 0, 
                                     'top': 0})()
    _buttons = []
    _labels = []
    _local_positions = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = None, None
        self.size = 0, 0
        self.disabled = True
        self.register_event_type("on_open")
        self.register_event_type("on_close")
        self.register_event_type("on_press_stack_button")
        self.register_event_type("on_release_stack_button")
        self._widget_declaration_finished = False
        Window.bind(on_resize=self._update_pos_buttons)
        Window.bind(on_maximize=self._update_pos_buttons)
        Window.bind(on_restore=self._update_pos_buttons)
        
    def on_enter(self, instance_button: MDFloatingBottomButton) -> None:
        """Called when the mouse cursor is over a button from the stack."""
        if self.state == "open":
            label = self._labels[self._buttons.index(instance_button)]
            if isinstance(label, MDFloatingLabel) and self.hint_animation:
                Animation.cancel_all(label)
                Animation(
                    _canvas_width=(-1 * (label.width + self.button_text_offset)
                                   * self._direction_vals[self.label_direction]),
                    d=self.opening_time,
                    t=self.opening_transition,
                ).start(instance_button)
                if (
                        instance_button.icon
                        == self.data[f"{label.text}"]
                        or instance_button.icon
                        == self.data[f"{label.text}"][0]
                ):
                    Animation(
                        opacity=1,
                        d=self.opening_time,
                        t=self.opening_transition,
                    ).start(label)
                else:
                    Animation(
                        opacity=0, d=0.1, t=self.opening_transition
                    ).start(label)

    def on_leave(self, instance_button: MDFloatingBottomButton) -> None:
        """Called when the mouse cursor goes outside the button of stack."""

        if self.state == "open":
            label = self._labels[self._buttons.index(instance_button)]
            if isinstance(label, MDFloatingLabel) and self.hint_animation:
                Animation.cancel_all(label)
                Animation(
                    _canvas_width=0,
                    d=self.opening_time,
                    t=self.opening_transition,
                    _elevation=0,
                ).start(instance_button)
                Animation(
                    opacity=0, d=0.1, t=self.opening_transition
                ).start(label)
                
    def on_parent(self, instance_self, instance_parent):
        if hasattr(instance_parent, "on_release") and hasattr(instance_parent, "on_press"):
            self.parent.bind(on_release=self.open_stack)
            self._update_pos_buttons()
        else:
            raise ValueError("Parent Widget must be a Button")
                
    def on_data(self, instance_stack_buttons, data: dict) -> None:
        """Creates a stack of buttons."""

        def on_data(*args):
            # Bottom buttons.
            Window.bind(on_draw=self._update_pos_buttons)
            for name, parameters in data.items():
                name_icon = (
                    parameters if (type(parameters) is str) else parameters[0]
                )

                bottom_button = MDFloatingBottomButton(
                    icon=name_icon,
                    on_enter=self.on_enter,
                    on_leave=self.on_leave,
                    opacity=0,
                )
                bottom_button.bind(
                    on_press=lambda x: self.dispatch("on_press_stack_button"),
                    on_release=lambda x: self.dispatch("on_release_stack_button"),
                )

                if "on_press" in parameters:
                    callback = parameters[parameters.index("on_press") + 1]
                    bottom_button.bind(on_press=callback)

                if "on_release" in parameters:
                    callback = parameters[parameters.index("on_release") + 1]
                    bottom_button.bind(on_release=callback)
                self._buttons.append(bottom_button)
                # Labels.
                label = None
                floating_text = name
                if floating_text:
                    label = MDFloatingLabel(text=floating_text, opacity=0)
                    label.bg_color = self.label_bg_color
                    label.radius = self.label_radius
                    label.text_color = (
                        self.label_text_color
                        if self.label_text_color
                        else self.theme_cls.text_color
                    )
                self._labels.append(label)
                self._local_positions.append(0)
                self.set_pos_bottom_buttons(bottom_button)
                if isinstance(label, MDFloatingLabel):
                    self.set_pos_labels(label)
            else:
                self._widget_declaration_finished = True

        self.remove_widgets()
        self._buttons = []
        self._labels = []
        self._local_positions = []
        self._anim_buttons_data = {}
        self._anim_labels_data = {}
        Clock.schedule_once(on_data)
        
    def set_pos_labels(self, instance_floating_label: MDFloatingLabel) -> None:
        """
        Sets the position of the floating labels.
        Called when the application's root window is resized.
        """
        if self._widget_declaration_finished:
            Window.unbind(on_draw=self._update_pos_buttons)
            self._widget_declaration_finished = False
        root = self.parent
        if root is None:
            root = self._root_button

        instance_floating_label.x = (root.center_x +
                                     self.button_text_offset *
                                     self._direction_vals[self.label_direction])
        instance_floating_label.x -= (dp(instance_floating_label.width)
                                      if self.label_direction == 'left'
                                      else 0)

        instance_floating_label.center_y = (self.parent.center_y +
                                            self._local_positions[
                                                self._labels.index(instance_floating_label)
                                            ])

    def set_pos_bottom_buttons(
            self, instance_floating_bottom_button: MDFloatingBottomButton
    ) -> None:
        """
        Sets the position of the bottom buttons in a stack.
        Called when the application's root window is resized.
        """
        root = self.parent
        if root is None:
            root = self._root_button
        instance_floating_bottom_button.center_x = root.center_x

        instance_floating_bottom_button.center_y = (
                self.parent.center_y +
                self._local_positions[
                    self._buttons.index(instance_floating_bottom_button)
                ])

    def touch_down(self, instance_window, touch):
        """ touch down event handler. """
        self._touch_started_inside = any([widget.collide_point(*touch.pos) 
                                          for widget in (self._buttons+self._labels)])
        if not self.auto_dismiss or self._touch_started_inside:
            self._window.on_touch_down(touch)
        return True
    
    def touch_move(self, instance_window, touch):
        """ touch moved event handler. """
        if not self.auto_dismiss or self._touch_started_inside:
            self._window.on_touch_move(touch)
        return True
    
    def touch_up(self, instance_window, touch):
        """ touch up event handler. """
        # Explicitly test for False as None occurs when shown by on_touch_down
        if self.auto_dismiss and self._touch_started_inside is False:
            self.close_stack()
        else:
            self._window.on_touch_up(touch)
        self._touch_started_inside = None
        return True
        
    def open_binding(self, *args):
        self._window.bind(on_touch_down=self.touch_down)
        self._window.bind(on_touch_move=self.touch_move)
        self._window.bind(on_touch_up=self.touch_up)

    def close_binding(self, *args):
        self.remove_widgets()
        self._window.unbind(on_touch_down=self.touch_down)
        self._window.unbind(on_touch_move=self.touch_move)
        self._window.unbind(on_touch_up=self.touch_up)
        
    def open_stack(self, instance_root_button: StackRootButton) -> None:
        for label in self._labels:
            if isinstance(label, MDFloatingLabel):
                Animation.cancel_all(label)

        if self.state != "open":
            y = 30 * self._direction_vals[self.stack_button_direction]
            anim_buttons_data = {}
            anim_labels_data = {}
            self._window = self.get_root_window()

            for i, button in enumerate(self._buttons):
                if isinstance(button, MDFloatingBottomButton):
                    # Sets new button positions.
                    y += dp(56) * self._direction_vals[self.stack_button_direction]
                    if not self._local_positions:
                        self._local_positions[i] = y
                    button.center_y += y
                    if not self._anim_buttons_data:
                        anim_buttons_data[button] = Animation(
                            opacity=1,
                            d=self.opening_time,
                            t=self.opening_transition,
                        )
                    label = self._labels[i]
                    if isinstance(label, MDFloatingLabel):
                        label.center_y = button.center_y
                        if not self._anim_labels_data:
                            anim_labels_data[label] = Animation(
                                opacity=1, d=self.opening_time
                            )

            if anim_buttons_data:
                self._anim_buttons_data = anim_buttons_data
            if anim_labels_data and not self.hint_animation:
                self._anim_labels_data = anim_labels_data

            self.disabled = False
            self.state = "open"
            self.dispatch("on_open")
            self.do_animation_open_stack(self._anim_buttons_data)
            self.do_animation_open_stack(self._anim_labels_data)
        else:
            self.close_stack()

    def do_animation_open_stack(self, anim_data: dict) -> None:
        """
        :param anim_data:
            {
                <kivymd.uix.button.MDFloatingBottomButton object>:
                    <kivy.animation.Animation>,
                <kivymd.uix.button.MDFloatingBottomButton object>:
                    <kivy.animation.Animation object>,
                ...,
            }
        """

        def on_progress(animation, widget, value):
            if value >= 0.1:
                animation_open_stack()

        def animation_open_stack(*args):
            try:
                widget = next(widgets_list)
                animation = anim_data[widget]
                animation.bind(on_progress=on_progress)
                animation.start(widget)
            except StopIteration:
                pass

        anim_root_start = Animation(size=self._window.size, 
                              d=self.opening_time)
        anim_root_start.bind(on_start=lambda x, y: self.add_widgets())
        anim_root_start.bind(on_complete=self.open_binding)
        anim_root_start.start(self._window)
        widgets_list = iter(list(anim_data.keys()))
        animation_open_stack()

    def close_stack(self):
        """Closes the button stack."""

        anim_root_end = Animation(size=self._window.size, 
                                      d=self.closing_time+0.1)
        anim_root_end.start(self._window)
        anim_root_end.bind(on_complete=self.close_binding)
        
        for button, label in zip(self._buttons, self._labels):
            if isinstance(button, MDFloatingBottomButton):
                Animation(
                    center_y=self.parent.center_y,
                    d=self.closing_time,
                    t=self.closing_transition,
                    opacity=0,
                ).start(button)
            if isinstance(label, MDFloatingLabel):
                if label.opacity > 0:
                    Animation(opacity=0, d=0.01).start(label)

        self.disabled = True
        self.state = "close"
        self.dispatch("on_close")

    def add_widget(self, widget, *args, **kwargs):
        if self._window is not None and widget.parent is None:
            self._window.add_widget(widget)

    def add_widgets(self):
        for i, button in enumerate(self._buttons):
            if isinstance(button, MDFloatingBottomButton):
                self.add_widget(button)
            label = self._labels[i]
            if isinstance(label, MDFloatingLabel):
                self.add_widget(label)

    def remove_widget(self, widget, *args, **kwargs):
        if self._window is not None:
            self._window.remove_widget(widget)

    def remove_widgets(self):
        for i, button in enumerate(self._buttons):
            if isinstance(button, MDFloatingBottomButton):
                self.remove_widget(button)
            label = self._labels[i]
            if isinstance(label, MDFloatingLabel):
                self.remove_widget(label)

    def _update_pos_buttons(self, instance=None, width=None, height=None):
        # Updates button positions when resizing screen.
        for widget in (self._buttons + self._labels):
            if isinstance(widget, MDFloatingBottomButton):
                self.set_pos_bottom_buttons(widget)
            elif isinstance(widget, MDFloatingLabel):
                self.set_pos_labels(widget)

    def _set_button_property(
            self, instance, property_name: str, property_value: str | list
    ):
        def set_count_widget(*args):
            if self._window.children:
                for widget in (self._buttons + self._labels):
                    if isinstance(widget, instance):
                        setattr(instance, property_name, property_value)
                        Clock.unschedule(set_count_widget)
                        break

        Clock.schedule_interval(set_count_widget, 0)

    def on_label_direction(self, *args):
        for label in self._labels:
            if isinstance(label, MDFloatingLabel):
                self.set_pos_labels(label)

    def on_stack_button_direction(self, *args):
        for button in self._buttons:
            if isinstance(button, MDFloatingBottomButton):
                self.set_pos_bottom_buttons(button)

    def on_label_text_color(self, instance_speed_dial, color: list | str) -> None:
        for label in self._labels:
            if isinstance(label, MDFloatingLabel):
                label.text_color = color

    def on_color_icon_stack_button(self, instance_speed_dial, color: list) -> None:
        self._set_button_property(MDFloatingBottomButton, "icon_color", color)

    def on_hint_animation(self, instance_speed_dial, value: bool) -> None:
        for label in self._labels:
            if isinstance(label, MDFloatingLabel):
                label.md_bg_color = (0, 0, 0, 0)

    def on_bg_hint_color(self, instance_speed_dial, color: list) -> None:
        setattr(MDFloatingBottomButton, "_bg_color", color)

    def on_bg_color_stack_button(self, instance_speed_dial, color: list) -> None:
        self._set_button_property(MDFloatingBottomButton, "md_bg_color", color)

    def on_open(self, *args):
        """Called when a stack is opened."""

    def on_close(self, *args):
        """Called when a stack is closed."""

    def on_press_stack_button(self, *args):
        """Called at the on_press event for the stack button"""

    def on_release_stack_button(self, *args):
        """Called at the on_release event for the stack button"""
