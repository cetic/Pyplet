---
title: Gradient Descent Playground
---

# Example: Gradient Descent Playground

A 1D optimization playground that visualizes gradient-based optimizers entirely in the browser. Adjust objectives, hyperparameters, and transport controls to see how each optimizer behaves in real time.

## Location

- Repository: `git@git.cetic.be:seglab/pyplet_examples.git`
- Path: `apps/examples/gradient_descent_playground_*`
- Client entry point: `gradient_descent_playground_client.py`
- Server shim: `gradient_descent_playground_server.py`

Pull the examples repository (submodule) after cloning Pyplet:

```bash
git submodule update --init --recursive
```

## Highlights

- Objective catalogue defined in `gradient_descent_playground_client.py:92` with Autograd-backed functions.
- Control panel (function, optimizer, hyperparameters, transport buttons) lives in
  `gradient_descent_playground_client.py:249` and no longer includes the former
  diagnostics sidebar, keeping the layout focused on interaction.
- Slider proxies in `gradient_descent_playground_client.py:362` feed hyperparameter updates into the simulation loop.
- Optimizer step logic centralised in `gradient_descent_playground_client.py:974`.
- Canvas rendering pipeline anchored by `gradient_descent_playground_client.py:1048`.

## Extending the playground

- Add new objectives by extending the `FUNCTIONS` mapping and wiring corresponding widgets in `render_layout`.
- Introduce optimizers by updating `apply_optimizer_step` and the UI controls that expose new hyperparameters.

Refer to the example repository README for a deeper walkthrough of the architecture and implementation notes.
