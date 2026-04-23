# Implement Poly Level Requests with cexprtk

This plan outlines the implementation of mathematical expression evaluation against G-Buffer data using `cexprtk`. It respects the existing MVC architecture and introduces a new visual overlay for requested pixels.

## Design Decisions
- **Performance**: We will run the evaluation in a background thread and show a progress bar/loading state so the UI doesn't freeze.
- **Visuals**: The mask will be applied directly to the currently viewed composite mode. A "CLEAR" button will be added to remove the mask.

## Proposed Variables for Injection

The following variables will be extracted from the EXR channels and injected into the `cexprtk` symbol table for expression evaluation:

- **Albedo**: `R`, `G`, `B`
- **World Position**: `WP_X`, `WP_Y`, `WP_Z`
- **Normals**: `N_X`, `N_Y`, `N_Z`
- **Depth**: `Z`
- **Metadata**: 
  - `TH` (TextureHash)
  - `PC` (PolyCount)
  - `MID` (Raw Material ID)
  - `MID_OPAQUE` (1 if list type is Opaque, else 0)
  - `MID_OPAQUE_MOD` (1 if list type is Opaque Mod, else 0)
  - `MID_TRANSLUCENT` (1 if list type is Translucent, else 0)
  - `MID_TRANSLUCENT_MOD` (1 if list type is Translucent Mod, else 0)
  - `MID_PUNCH_THROUGH` (1 if list type is Punch-Through, else 0)
  - `MID_HAS_TEX` (Decomposed: 1 if texture, 0 otherwise)
  - `MID_GOURAUD` (Decomposed: 1 if gouraud, 0 otherwise)
  - `MID_HAS_BUMP` (Decomposed: 1 if bumpmap, 0 otherwise)
  - `MID_FOG` (Decomposed: 1 if fog control, 0 otherwise)

## Proposed Changes

---

### App State
Updates to store the evaluation result.

#### [MODIFY] `core/app_state.py`
- Add `self.expression_mask = None` to store the resulting boolean/alpha mask.

---

### Main Controller
Wiring the UI callbacks and managing the display of the mask.

#### [MODIFY] `main.py`
- Wire `self.callbacks['on_eval_poly'] = self.main_ctrl.on_eval_poly`.
- Wire `self.callbacks['on_eval_pixel'] = self.main_ctrl.on_eval_pixel`.
- Wire `self.callbacks['on_clear_mask'] = self.main_ctrl.on_clear_mask`.

#### [MODIFY] `controllers/main_controller.py`
- Add `on_eval_poly(self)` and `on_eval_pixel(self)` which read the text from the UI entries and call `InteractionController` or a dedicated evaluation method.
- Add `on_clear_mask(self)` to set `self.state.expression_mask = None` and refresh.
- Update `refresh_image_display(self)`: Before converting the image to PIL for display, check if `self.state.expression_mask` is set. If true, blend a red overlay (e.g., RGBA `255, 0, 0, 128`) over the `self.state.last_numpy_image` where the mask is positive.

---

### Interaction / Expression Controller
Implementing the `cexprtk` logic.

#### [MODIFY] `controllers/interaction_controller.py` (or a new `QueryController`)
- Implement `evaluate_expression(self, expr_string)`:
  - Extract the necessary channels (WP_X, WP_Y, WP_Z, R, G, B, etc.) from `self.mc.state.current_exr_data` as 1D/2D arrays.
  - Compile the `cexprtk` expression using `cexprtk.Symbol_Table` and `cexprtk.Expression`.
  - Iterate over the pixels. To avoid freezing the UI, this should ideally be dispatched to a background worker thread (`threading.Thread`).
  - Set `self.mc.state.expression_mask` with the boolean results where the expression evaluates to `> 0` or `True`.
  - Trigger `self.mc.refresh_image_display()`.
  - Log errors to the bottom panel console if the syntax is invalid or variables are missing.

#### [MODIFY] `ui/components/bottom_panel.py`
- Modify `on_eval_poly` to pass the content of `self.poly_req_entry` to the callback.
- Add a "CLEAR" button next to "EVALUATE" that triggers the `on_clear_mask` callback.

## Verification Plan

### Manual Verification
1. Open an EXR file containing metadata channels.
2. Navigate to the "Poly Request" tab in the bottom panel.
3. Enter an expression like `WP_Y > 10` or `MID == 42`.
4. Click "EVALUATE".
5. Observe the UI "LOADING..." indicator.
6. Verify that a semi-transparent red mask appears precisely over the pixels that satisfy the expression.
7. Check the console tab for any parsing errors or syntax issues reported by `cexprtk`.
