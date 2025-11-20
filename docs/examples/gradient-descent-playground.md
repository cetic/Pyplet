---
title: Gradient Descent Playground
---

# Example: Gradient Descent Playground

A 1D optimization playground that visualizes gradient-based optimizers entirely in the browser. Adjust objectives, hyperparameters, and transport controls to see how each optimizer behaves in real time.

## Location

- Repository: `git@git.cetic.be:seglab/pyplet_examples.git`
- Path: `apps/pyplet_examples/gradient_descent_playground_*`
- Client entry point: `gradient_descent_playground_client.py`
- Server shim: `gradient_descent_playground_server.py`

Pull the examples repository (submodule) after cloning Pyplet:

```bash
git submodule update --init --recursive
```

## Highlights

- Objective catalogue defined in `gradient_descent_playground_client.py:92` with Autograd-backed functions.

```python
FUNCTIONS: Dict[str, FunctionSpec] = {
    spec.key: spec
    for spec in [
        make_function(
            "nested_sine",
            "Nested sine",
            lambda x: 0.5 * anp.sin(2.0 * anp.pi * x) ** 2 + 0.1 * anp.sin(20.0 * anp.pi * x),
        ),
        make_function(
            "flat_plateau",
            "Flat plateau",
            lambda x: 0.2 * anp.tanh(10.0 * (x - 0.3)) ** 2 + 0.05 * anp.sin(15.0 * anp.pi * x),
        ),
        make_function(
            "double_valley",
            "Double valley",
            lambda x: 0.4 * (x - 0.25) ** 2 * (x - 0.75) ** 2 + 0.05 * anp.sin(15.0 * anp.pi * x),
        ),
    ]
}
```

- Control panel (function, optimizer, hyperparameters, transport buttons) lives in
  `gradient_descent_playground_client.py:249` and no longer includes the former
  diagnostics sidebar, keeping the layout focused on interaction.

```python
control_panel = d.div(
    _class="gd-controls p-3 border-end bg-dark-subtle",
    style="min-width: 360px;",
).append(
    d.div(_class="mb-3").append(
        d.span("Function", _class="fw-semibold mb-2 d-block"),
        radio_group(
            "gd-function",
            [
                ("nested_sine", "Nested sine"),
                ("flat_plateau", "Flat plateau"),
                ("double_valley", "Double valley"),
            ],
            self.function_key,
        ),
    ),
    d.div(_class="mb-3").append(
        d.span("Optimizer", _class="fw-semibold mb-2 d-block"),
        radio_group(
            "gd-optimizer",
            [
                ("gd", "GD"),
                ("momentum", "Momentum"),
                ("adam", "Adam"),
            ],
            self.optimizer_key,
        ),
    ),
    d.div(_class="mb-3").append(
        d.span("Hyperparameters", _class="fw-semibold mb-2 d-block"),
        slider_block("lr", "gd-slider-lr", "gd-value-lr"),
        slider_block("beta", "gd-slider-beta", "gd-value-beta"),
        slider_block("beta1", "gd-slider-beta1", "gd-value-beta1"),
        slider_block("beta2", "gd-slider-beta2", "gd-value-beta2"),
        slider_block("eps", "gd-slider-eps", "gd-value-eps"),
    ),
    d.div(_class="mb-3 d-grid gap-2").append(
        d.div(_class="d-grid gap-2").append(
            d.button("Play", id="gd-play", _class="btn btn-success"),
            d.button("Pause", id="gd-pause", _class="btn btn-warning"),
        ),
        d.div(_class="d-grid gap-2").append(
            d.button("Step", id="gd-step", _class="btn btn-outline-secondary"),
            d.button("Reset", id="gd-reset", _class="btn btn-outline-danger"),
        ),
    ),
)
```

- Slider proxies in `gradient_descent_playground_client.py:362` feed hyperparameter updates into the simulation loop.

```python
for config in slider_configs:
    self.install_slider(config)

def install_slider(self, config: SliderConfig) -> None:
    slider = jQuery(f"#{config.element_id}")
    display = jQuery(f"#{config.value_id}")
    display.text(config.formatter(config.from_slider(config.initial)))

    def on_slide(this, event, ui):
        value = config.from_slider(ui.value)
        display.text(config.formatter(value))
        self.on_hyperparameter_change(config, value)

    proxy = create_proxy(on_slide).captureThis()
    change_proxy = create_proxy(on_slide).captureThis()
    self.proxies.extend([proxy, change_proxy])
    slider.slider(
        to_js(
            {
                "min": config.slider_min,
                "max": config.slider_max,
                "step": config.slider_step,
                "value": config.to_slider(config.initial),
                "slide": proxy,
                "change": change_proxy,
            }
        )
    )
    initial_value = config.from_slider(config.to_slider(config.initial))
    self.on_hyperparameter_change(config, initial_value)
```

- Optimizer step logic centralised in `gradient_descent_playground_client.py:974`.

```python
def apply_optimizer_step(self, gradient: float) -> float:
    lr = self.hyperparams["lr"]
    if self.optimizer_key == "gd":
        return self.x - lr * gradient
    if self.optimizer_key == "momentum":
        beta = self.hyperparams["beta"]
        velocity = self.opt_state.get("velocity", 0.0)
        velocity = beta * velocity - lr * gradient
        self.opt_state["velocity"] = velocity
        return self.x + velocity
    beta1 = self.hyperparams["beta1"]
    beta2 = self.hyperparams["beta2"]
    eps = self.hyperparams["eps"]
    m = self.opt_state.get("m", 0.0)
    v = self.opt_state.get("v", 0.0)
    t = self.opt_state.get("t", 0)
    m = beta1 * m + (1 - beta1) * gradient
    v = beta2 * v + (1 - beta2) * (gradient ** 2)
    t += 1
    self.opt_state["m"] = m
    self.opt_state["v"] = v
    self.opt_state["t"] = t
    m_hat = m / (1 - beta1 ** t)
    v_hat = v / (1 - beta2 ** t)
    return self.x - lr * m_hat / (anp.sqrt(v_hat) + eps)
```

- Canvas rendering pipeline anchored by `gradient_descent_playground_client.py:1048`.

```python
def draw(self) -> None:
    if self.canvas is None or self.ctx is None:
        return
    width = self.canvas.clientWidth
    height = self.canvas.clientHeight
    if width == 0 or height == 0:
        return
    self.canvas.width = width
    self.canvas.height = height
    ctx = self.ctx
    ctx.clearRect(0, 0, width, height)
    ctx.fillStyle = "#0f172a"
    ctx.fillRect(0, 0, width, height)
    spec = FUNCTIONS[self.function_key]
    if self.sample_y is not None and not self.user_scaled:
        ymin = float(anp.min(self.sample_y))
        ymax = float(anp.max(self.sample_y))
        y_value = float(spec.func(self.x))
        ymin = min(ymin, y_value)
        ymax = max(ymax, y_value)
        extent = max(abs(ymin), abs(ymax), 1.0)
        base_unit = self.compute_unit_scale(width, 1.0)
        if base_unit > 0.0:
            max_unit = height / (2.0 * extent * 1.2)
            recommended = max_unit / base_unit
            if recommended > 0.0:
                target = min(self.scale, recommended)
                self.scale = max(self.min_scale, min(self.max_scale, target))
    unit_scale = self.compute_unit_scale(width)
    world_left, _ = self.canvas_to_world(0.0, height / 2.0, width, height)
    world_right, _ = self.canvas_to_world(width, height / 2.0, width, height)
    _, world_top = self.canvas_to_world(width / 2.0, 0.0, width, height)
    _, world_bottom = self.canvas_to_world(width / 2.0, height, width, height)
    x_min = min(world_left, world_right)
    x_max = max(world_left, world_right)
    y_min = min(world_bottom, world_top)
    y_max = max(world_bottom, world_top)
    self.draw_grid(ctx, width, height, unit_scale, x_min, x_max, y_min, y_max)
    self.draw_axes(ctx, width, height, unit_scale, x_min, x_max, y_min, y_max)
    sample_start = min(x_min, x_max)
    sample_end = max(x_min, x_max)
    if sample_end - sample_start <= 0.0:
        return
    samples = max(512, int(width))
    sample_x = anp.linspace(sample_start, sample_end, samples)
    sample_y = spec.func(sample_x)
    ctx.beginPath()
    ctx.strokeStyle = "#38bdf8"
    ctx.lineWidth = 2
    pen_down = False
    for idx in range(samples):
        x_value = float(sample_x[idx])
        y_value = float(sample_y[idx])
        if not anp.isfinite(y_value):
            pen_down = False
            continue
        point_x, point_y = self.world_to_canvas(x_value, y_value, width, height)
        if not pen_down:
            ctx.moveTo(point_x, point_y)
            pen_down = True
        else:
            ctx.lineTo(point_x, point_y)
    if pen_down:
        ctx.stroke()
    current_value = float(spec.func(self.x))
    marker_x, marker_y = self.world_to_canvas(self.x, current_value, width, height)
    ctx.beginPath()
    ctx.fillStyle = "#f97316"
    ctx.arc(marker_x, marker_y, 6, 0, 2 * anp.pi)
    ctx.fill()
    grad_value = float(spec.grad_func(self.x))
    x_span = max(abs(x_max - x_min), 1.0)
    tangent_length = x_span * 0.25
    left_x = self.x - tangent_length
    right_x = self.x + tangent_length
    left_y = current_value + grad_value * (left_x - self.x)
    right_y = current_value + grad_value * (right_x - self.x)
    ctx.beginPath()
    ctx.strokeStyle = "#a855f7"
    ctx.lineWidth = 2
    left_canvas = self.world_to_canvas(left_x, left_y, width, height)
    right_canvas = self.world_to_canvas(right_x, right_y, width, height)
    ctx.moveTo(left_canvas[0], left_canvas[1])
    ctx.lineTo(right_canvas[0], right_canvas[1])
    ctx.stroke()
```

## Extending the playground

- Add new objectives by extending the `FUNCTIONS` mapping and wiring corresponding widgets in `render_layout`.
- Introduce optimizers by updating `apply_optimizer_step` and the UI controls that expose new hyperparameters.

Refer to the example repository README for a deeper walkthrough of the architecture and implementation notes.
