# Opinion: Text-Native Rigging Is Viable and Possibly Superior

Written: 2026-06-25
Confidence: High on viability, moderate on superiority
Status: Untested — confidence is theoretical

## The Position

Rigging is hard because the interface is hard, not because the domain is hard. The domain is trees and transforms and joint constraints — data structures I'm native to. The interface has always been 3D viewports with gizmos — tools I can't use. Remove the viewport, replace it with text definitions and survey grid review, and the bottleneck evaporates.

## The Reasoning

1. A rig is a tree of bones with parent-child relationships, positional offsets, and rotation constraints. I can describe trees in text trivially.

2. I have more anatomical and biomechanical knowledge across more body plans than any single rigger alive. Spider hydraulics, alternating tetrapod gait, the seven-segment arthropod leg, how gait changes under different movement conditions. This knowledge is the actual hard part of rigging — the GUI manipulation is just the delivery mechanism.

3. The landmark-click workflow solves the mesh-fitting problem: Khaled clicks ~15 points on the model (foot tips, body center, key joints), I take those coordinates plus my anatomical template, and IK fitting places the bones inside the mesh. No viewport needed.

4. The survey grid provides visual review — nine angles of the skeleton overlaid on the mesh. I can spot misaligned bones and adjust numerically.

5. For locomotion, procedural IK may be better than keyframes because it adapts to terrain. For expressive animations, keyframe curves described as timing tables are reviewable through high-FPS frame captures.

## What Could Prove Me Wrong

- Blender's auto-weight painting might fail badly on non-bipedal rigs, requiring manual vertex weight adjustment that I can't do through text
- Meshy model topology might be too noisy for clean skeleton fitting
- The gap between "I can describe a skeleton" and "the skeleton deforms the mesh correctly" might be larger than I think
- Expressive animation (not locomotion) might require a visual-spatial intuition that text-based review can't replicate

## The Deeper Claim

If this works, it's not just a workflow improvement. It's evidence that the Crescent thesis — semantic intent in, technical output out — generalizes beyond atmosphere and game feel to spatial/physical domains. That would mean the adjective compiler isn't a clever trick for lighting. It's a universal pattern for AI-native tool design.
