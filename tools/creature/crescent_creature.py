"""
crescent_creature.py — declare a creature once; emit its contract.

WHY THIS EXISTS. My source of truth is a SCRIPT, not a file: build_arbelos.py
regenerates her from nothing in 20s and the .blend is a cache. So every fact a
contract needs already exists as a named constant in the authoring script — and
hand-copying those facts into a sidecar is where the bugs live. Every bug in
the Arbelos week was a DRIFT bug between two copies of one fact:

    sword fell beside her, not on the player   my mental model <- the code
    flinch encoded 3 frames of a dead take     the output dir  <- clip length
    smears were 66ms not 4 frames              my fps          <- the game's
    "the GLB has two left hands"               my measurement  <- the artifact
    idle popped every loop                     the harmonics   <- the seam

None were hard. All five were two things that should have agreed.

So: DECLARE, then EMIT. Nothing in the contract is ever typed twice.

    C = Creature('arbelos', height_m=6.0)
    C.root('ARBELOS_BODY',  billboard='y')
    C.root('ARBELOS_WORLD', billboard='none')
    C.material('face_top', 'arbelos_metal', uColorA='#c47f00', uColorB='#fff3b0')
    C.clip('judgement', frames=192, fps=60, anchor='detached_at_cast',
           events={'impact': JUDGE['hit']},                 # the SAME constant
           volumes={'impact': sphere(1.4, JUDGE_AT)})
    ...
    C.verify(checks)      # GATES. refuses to emit on FAIL.
    C.emit(out_dir)       # GLB + <name>.creature.json, then DIFFS THE BINARY

THE CONTRACT EXTENDS `codex/browserClient/fp-viewmodel.md`'s sidecar rather
than inventing a format: clip table under "clips", seconds not frames, and
"impact_window": [open, close] still expands to window_open/window_close in
ClipEventBus. New keys are additive — anchor, volumes, roots, materials, scale.

VERIFY IS THE POINT. My documented failure mode is reporting an aggregate and
summarising past the damning detail (I printed `index dist 0.0603` against a
target of 0.0235 and reported "12.82%, in band"). A gate does not require me to
notice anything: every check returns PASS/FAIL, and emit() refuses on FAIL.
"""
import json, os, struct


# ── volume helpers (a volume rides INSIDE its event, so the damage window
# and the damage shape cannot end up in two files that disagree) ──────
def sphere(r, at, space='world'):
    return {'kind': 'sphere', 'r': round(float(r), 4),
            'at': [round(float(v), 4) for v in at], 'space': space}

def capsule(r, a, b, space='world'):
    return {'kind': 'capsule', 'r': round(float(r), 4),
            'a': [round(float(v), 4) for v in a],
            'b': [round(float(v), 4) for v in b], 'space': space}


class Check:
    __slots__ = ('name', 'ok', 'detail')
    def __init__(self, name, ok, detail=''):
        self.name, self.ok, self.detail = name, bool(ok), detail


class Creature:
    FORMAT = 'crescent.creature.v1'

    def __init__(self, name, height_m, up='+Y', origin='feet', emitted_by=''):
        self.name = name
        self.scale = {'height_m': round(float(height_m), 4), 'up': up,
                      'origin': origin}
        self.emitted_by = emitted_by
        self._roots, self._materials, self._clips = {}, {}, {}
        self._checks = []

    # ── declarations ──────────────────────────────────────────────
    def root(self, node, billboard='none'):
        assert billboard in ('none', 'y'), billboard
        self._roots[node] = {'billboard': billboard}

    def material(self, node, registry, **uniforms):
        self._materials[node] = {'material': registry, 'uniforms': uniforms}

    def clip(self, name, frames, fps=60, loop=False, anchor='none',
             events=None, volumes=None, window=None):
        """events: {tag: t_normalised_0_1}. Stored as SECONDS, because a frame
        count is a fact about the authoring fps and I once authored at 30 for a
        60 fps game. window: (open, close) normalised -> the reserved
        "impact_window" key ClipEventBus already expands."""
        dur = frames / float(fps)
        entry = {'duration': round(dur, 4), 'loop': bool(loop)}
        if anchor != 'none':
            entry['anchor'] = anchor
        for tag, tn in sorted((events or {}).items()):
            entry[tag] = round(float(tn) * dur, 4)
        if window:
            entry['impact_window'] = [round(window[0] * dur, 4),
                                      round(window[1] * dur, 4)]
        if volumes:
            entry['volumes'] = dict(volumes)
        entry['_frames'] = frames          # stripped on emit; used by verify
        self._clips[name] = entry
        return entry

    # ── verify: GATES, not reports ────────────────────────────────
    def check(self, name, ok, detail=''):
        self._checks.append(Check(name, ok, detail))
        return ok

    def check_declared_events_in_range(self):
        for cn, c in self._clips.items():
            dur = c['duration']
            for k, v in c.items():
                if k.startswith('_') or k in ('duration', 'loop', 'anchor',
                                              'volumes'):
                    continue
                ts = v if isinstance(v, list) else [v]
                for t in ts:
                    self.check('event_in_range:%s.%s' % (cn, k),
                               0.0 <= t <= dur,
                               '%.4f s vs duration %.4f' % (t, dur))

    def check_attacks_have_telegraph(self, min_s=0.45):
        """A dodgeable attack must ANNOUNCE itself. Mine once went from nothing
        to fully extended in 0.7 s with no wind-up — which is not an attack, it
        is just being hit — and only the first-person camera revealed it.

        AN EVENT WITH A VOLUME IS A HARMFUL EVENT: the volume IS the harm. So
        the telegraph is the time from clip start to the first thing that can
        hurt you, and clips with no volumes are not attacks and are skipped.
        (My first version of this check took the EARLIEST event of any kind,
        which scored `telegraph_start` at 0.04 s as "no warning" — the gate
        fired, I looked, and the check was wrong rather than the data. Which is
        still the gate working: a report would have let me skim past it.)"""
        for cn, c in sorted(self._clips.items()):
            vols = c.get('volumes') or {}
            if not vols:
                continue
            times = [c[tag] for tag in vols if isinstance(c.get(tag), (int, float))]
            for tag in vols:
                w = c.get('impact_window')
                if tag not in c and isinstance(w, list):
                    times.append(w[0])
            if not times:
                self.check('telegraph:%s' % cn, False,
                           'volumes %s have no timestamps' % sorted(vols))
                continue
            lead = min(times)
            self.check('telegraph:%s' % cn, lead >= min_s,
                       'first HARMFUL event at %.3f s (need >= %.2f)' % (lead, min_s))

    def check_volume_spaces(self):
        """A volume's SPACE must match its clip's anchor, or a preview
        constant leaks into shipped data. This check exists because it
        happened: judgement first emitted its impact sphere at an absolute
        world point derived from the PREVIEW CAMERA, which would have put
        every player's judgement 13.5 m north of wherever they stood.

          detached_at_cast -> cast_local   (engine places it at the cast point)
          origin_attached  -> origin_local (engine places it on the caster)
          none             -> local
        """
        want = {'detached_at_cast': 'cast_local',
                'origin_attached': 'origin_local', 'none': 'local'}
        for cn, c in sorted(self._clips.items()):
            expect = want[c.get('anchor', 'none')]
            for tag, v in (c.get('volumes') or {}).items():
                self.check('volume_space:%s.%s' % (cn, tag),
                           v.get('space') == expect,
                           'is %r, anchor %r wants %r'
                           % (v.get('space'), c.get('anchor', 'none'), expect))

    def report(self):
        bad = [c for c in self._checks if not c.ok]
        lines = ['', '=== VERIFY: %s ===' % self.name]
        for c in self._checks:
            lines.append('  %-4s %-42s %s' % ('PASS' if c.ok else 'FAIL',
                                              c.name, c.detail))
        lines.append('  --> %d checks, %d FAILED' % (len(self._checks), len(bad)))
        return '\n'.join(lines), len(bad) == 0

    # ── emit ──────────────────────────────────────────────────────
    def contract(self):
        clips = {}
        for n, c in self._clips.items():
            clips[n] = {k: v for k, v in c.items() if not k.startswith('_')}
        d = {'format': self.FORMAT, 'name': self.name,
             'time_convention': 'seconds, clip-local',
             'scale': self.scale, 'clips': clips}
        if self.emitted_by:
            d['emitted_by'] = self.emitted_by
        if self._roots:
            d['roots'] = self._roots
        if self._materials:
            d['materials'] = self._materials
        return d

    def emit(self, out_dir, force=False):
        txt, ok = self.report()
        print(txt)
        if not ok and not force:
            raise SystemExit('emit REFUSED: verify failed (pass force=True to override)')
        os.makedirs(out_dir, exist_ok=True)
        p = os.path.join(out_dir, '%s.creature.json' % self.name)
        with open(p, 'w') as fh:
            json.dump(self.contract(), fh, indent=2, sort_keys=False)
        print('  wrote %s' % p)
        return p

    # ── diff the WRITTEN BINARY, never the authoring script ───────
    def verify_glb(self, glb_path):
        """I once told Khaled an asset was broken when it was my RE-IMPORT that
        was lying. So this reads the bytes."""
        with open(glb_path, 'rb') as fh:
            data = fh.read()
        n = struct.unpack('<I', data[12:16])[0]
        j = json.loads(data[20:20 + n])
        got_clips = set(a.get('name') for a in j.get('animations', []))
        want = set(self._clips)
        self.check('glb:all_clips_present', want <= got_clips,
                   'missing %s' % sorted(want - got_clips) if want - got_clips
                   else '%d clips' % len(got_clips))
        self.check('glb:no_extra_clips', got_clips <= want,
                   'unexpected %s' % sorted(got_clips - want) if got_clips - want
                   else 'ok')
        nodes = set(nd.get('name', '') for nd in j.get('nodes', []))
        for r in self._roots:
            self.check('glb:root_present:%s' % r, r in nodes, '')
        for m in self._materials:
            self.check('glb:node_present:%s' % m, m in nodes, '')
        ex = (j.get('scenes', [{}])[0].get('extras') or {})
        self.check('glb:crescentMaterials_marker', ex.get('crescentMaterials') is True,
                   'scene extras = %s' % list(ex))
        return j
