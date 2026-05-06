import os
from typing import Optional

from agency_swarm.tools import BaseTool
from pydantic import Field

# Voice samples live in the agent's files directory
VOICE_SAMPLES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "files", "voice_samples")
)


class VoiceLibrary(BaseTool):
    """
    Load approved writing samples from Ellah's voice library to calibrate tone,
    preferred phrasing, and vocabulary for a draft.

    Use this at the start of any drafting task that will be sent externally — donor
    letters, board communications, LinkedIn posts, op-eds, or partner outreach.
    Returns a tone profile and style guide that should anchor the draft.

    Voice samples are stored in communications_agent/files/voice_samples/.
    Add .txt files there to expand the library.

    Actions:
    - 'load'    — load voice samples and return a tone calibration profile
    - 'list'    — list available voice sample files
    - 'add_tip' — record a style tip to the voice library notes file
    """

    action: str = Field(
        "load",
        description="Action: 'load' (default), 'list', or 'add_tip'",
    )
    sample_type: Optional[str] = Field(
        None,
        description=(
            "Filter samples by type: 'donor', 'board', 'partner', 'thought_leadership', "
            "'grant', or 'event'. If not specified, loads all available samples."
        ),
    )
    tip: Optional[str] = Field(
        None,
        description="Style tip to add to the voice library notes (required for 'add_tip')",
    )

    def run(self):
        os.makedirs(VOICE_SAMPLES_DIR, exist_ok=True)

        if self.action == "list":
            return self._list_samples()
        elif self.action == "add_tip":
            if not self.tip:
                return "Error: 'add_tip' requires a tip."
            return self._add_tip()
        else:
            return self._load_samples()

    def _list_samples(self) -> str:
        files = [f for f in os.listdir(VOICE_SAMPLES_DIR) if f.endswith(".txt")]
        if not files:
            return (
                f"No voice samples found in {VOICE_SAMPLES_DIR}.\n"
                "To add samples: paste Ellah's existing communications (donor letters, "
                "board memos, LinkedIn posts, etc.) as .txt files into "
                "communications_agent/files/voice_samples/."
            )
        lines = [f"Voice samples ({len(files)} files):", "=" * 40]
        for f in sorted(files):
            size = os.path.getsize(os.path.join(VOICE_SAMPLES_DIR, f))
            lines.append(f"  {f}  ({size:,} bytes)")
        return "\n".join(lines)

    def _load_samples(self) -> str:
        files = [f for f in os.listdir(VOICE_SAMPLES_DIR) if f.endswith(".txt")]

        # Filter by type if requested
        if self.sample_type:
            files = [f for f in files if self.sample_type.lower() in f.lower()]

        if not files:
            # Return default profile if no samples yet
            return self._default_voice_profile()

        samples = []
        for fname in sorted(files)[:6]:  # Cap at 6 samples to avoid token overload
            fpath = os.path.join(VOICE_SAMPLES_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read(2000)
                samples.append(f"--- Sample: {fname} ---\n{content}")
            except Exception:
                continue

        # Load notes file if it exists
        notes_file = os.path.join(VOICE_SAMPLES_DIR, "_style_notes.txt")
        notes_content = ""
        if os.path.exists(notes_file):
            with open(notes_file, "r", encoding="utf-8") as f:
                notes_content = f.read(1000)

        profile_lines = [
            "# Ellah Ronen — Voice Calibration Profile",
            "",
            self._default_voice_profile(),
            "",
        ]
        if notes_content:
            profile_lines.append("## Accumulated Style Notes")
            profile_lines.append(notes_content)
            profile_lines.append("")

        if samples:
            profile_lines.append("## Writing Samples (for tone reference)")
            profile_lines.extend(samples)

        return "\n".join(profile_lines)

    def _add_tip(self) -> str:
        notes_file = os.path.join(VOICE_SAMPLES_DIR, "_style_notes.txt")
        existing = ""
        if os.path.exists(notes_file):
            with open(notes_file, "r", encoding="utf-8") as f:
                existing = f.read()
        from datetime import datetime
        new_entry = f"\n[{datetime.now().strftime('%Y-%m-%d')}] {self.tip}"
        with open(notes_file, "w", encoding="utf-8") as f:
            f.write(existing + new_entry)
        return f"✓ Style tip added to voice library:\n  {self.tip}"

    def _default_voice_profile(self) -> str:
        return """## Core Voice Profile — Ellah Ronen

**Tone:** Executive but warm. Clear and direct. Not corporate. Not academic.
Jargon only when the audience expects it. Communications feel like they come
from a person, not an institution.

**Register by audience:**
- Major donors: Personal, appreciative, specific about impact. Never transactional.
- Foundation program officers: Professional, evidence-informed, mission-aligned.
  Match their language from their published priorities.
- Board members: Direct, concise, no hedging. Assume intelligence; explain context only when needed.
- Community members and program participants: Accessible, warm, respectful. Avoid sector jargon.
- Government officials: Formal but not bureaucratic. Lead with data and community need.
- Media: Concise, quotable, forward-looking.
- Peers and colleagues: Collegial, direct, honest.

**What Ellah's voice is:**
- Asset-based: communities are described by their strengths, not their deficits
- Systems-aware: she connects the immediate ask to broader context naturally
- Relationship-first: every communication is a moment in an ongoing relationship
- Authentic: no fake enthusiasm; genuine appreciation for the work and the people doing it

**What to avoid:**
- Generic nonprofit-speak: "impactful outcomes," "robust programming," "stakeholder engagement"
- Passive voice and hedge words: "it seems," "we hope," "perhaps"
- Over-formality: "Dear Mr./Ms. [Last Name]" when a first name is known
- AI-sounding openers: "I hope this email finds you well," "I am writing to..."

**Signature conventions:**
- LFLA communications: Ellah's name, title, LFLA letterhead
- Crestline Collective: Ellah's name, Principal, Crestline Collective
- Always confirm which org before drafting anything external

**Always confirm org context** before producing any communication with a signature,
letterhead, or organizational reference."""


if __name__ == "__main__":
    print("=== Test: Load default voice profile ===")
    tool = VoiceLibrary(action="load")
    print(tool.run())

    print("\n=== Test: Add a style tip ===")
    tool2 = VoiceLibrary(
        action="add_tip",
        tip="Ellah prefers 'community members' over 'constituents' or 'beneficiaries'.",
    )
    print(tool2.run())

    print("\n=== Test: List samples ===")
    tool3 = VoiceLibrary(action="list")
    print(tool3.run())
