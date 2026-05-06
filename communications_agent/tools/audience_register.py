from agency_swarm.tools import BaseTool
from pydantic import Field

# Register profiles keyed by audience type
AUDIENCE_PROFILES = {
    "major_donor": {
        "label": "Major Donor",
        "formality": "Personal and warm — not formal, not casual. First name always.",
        "opening_style": "Reference something specific: their giving history, a program they care about, or a recent interaction.",
        "tone_notes": "Appreciative without being effusive. Specific about impact. Never transactional.",
        "length": "Brief to moderate. 2–4 paragraphs for thank-yous and updates. More for cultivation or ask letters.",
        "avoid": "Generic language, passive voice, org-speak, anything that sounds like a form letter.",
        "sample_opener": "It was wonderful to see you at [event] last month — your support of [specific program] has made a real difference for...",
    },
    "foundation_program_officer": {
        "label": "Foundation Program Officer",
        "formality": "Professional and collegial. First name if the relationship exists; formal otherwise.",
        "opening_style": "Lead with the grant/proposal name and purpose or a brief status update. Program officers read a lot.",
        "tone_notes": "Evidence-informed, mission-aligned. Mirror their published language and priorities. Equity language expected.",
        "length": "Concise. Get to the point in the first paragraph. Use headings for longer documents.",
        "avoid": "Hyperbole, vague impact claims, failure to cite specifics, and anything that sounds like a sales pitch.",
        "sample_opener": "Thank you for considering [org]'s proposal for [program] — I'm writing to provide an update on [milestone/question].",
    },
    "board_member": {
        "label": "Board Member",
        "formality": "Direct and collegial. First name always. They are peers, not audiences.",
        "opening_style": "State the purpose immediately. Board members are busy and trust Ellah to be direct.",
        "tone_notes": "Concise, no hedging. Assume intelligence. Explain context only when genuinely new. Decisive.",
        "length": "Short. 1–2 paragraphs for most emails. Full memos for governance matters.",
        "avoid": "Over-explanation, excessive context, anything that reads like it was written for a general audience.",
        "sample_opener": "Quick update on [matter]: [concise status]. I need your input on [specific decision] by [date].",
    },
    "corporate_partner": {
        "label": "Corporate Partner or Prospect",
        "formality": "Professional. Formal first contact; collegial once relationship is established.",
        "opening_style": "Open with shared values or mission alignment — not a pitch. Corporate contacts are pitched constantly.",
        "tone_notes": "Business-clear. Lead with mutual benefit. Emphasize visibility, brand alignment, and employee engagement.",
        "length": "Moderate. 3–4 paragraphs for outreach. Decks handle the detail.",
        "avoid": "Charity framing, one-sided asks, failure to address what's in it for them.",
        "sample_opener": "[Company]'s commitment to [relevant value/program] aligns closely with what we do at [org] — I wanted to introduce an opportunity that might be a natural fit.",
    },
    "community_member": {
        "label": "Community Member or Program Participant",
        "formality": "Warm and accessible. Plain language. No sector jargon.",
        "opening_style": "Begin with the person or community — not the org. Lead with relevance to them.",
        "tone_notes": "Respectful, clear, empowering. Asset-based. Not condescending.",
        "length": "Brief. Short sentences, plain words, clear call to action.",
        "avoid": "Jargon, passive voice, anything that centers the org's needs over the community's.",
        "sample_opener": "We have something for you — [short description of program/resource] is available to [eligibility], and we'd love to see you there.",
    },
    "government_official": {
        "label": "Government Official (elected or appointed)",
        "formality": "Formal. Title and last name unless invited to use first name.",
        "opening_style": "Lead with the constituency or community benefit. Officials respond to constituent impact data.",
        "tone_notes": "Data-forward, community-grounded. Connect the ask to their district or policy priorities.",
        "length": "Two to three paragraphs for emails. Attach one-pager if requesting action.",
        "avoid": "Advocacy that crosses into political positioning, vague asks, failure to cite data.",
        "sample_opener": "Dear [Title] [Last Name], On behalf of [org], I'm writing to share an opportunity that directly benefits residents in [district/area]...",
    },
    "media": {
        "label": "Media / Journalist",
        "formality": "Professional but direct. First name is fine.",
        "opening_style": "Lead with the news hook in the subject line and first sentence. Do not bury the lead.",
        "tone_notes": "Quotable, forward-looking, specific. Avoid boilerplate press release language.",
        "length": "Very brief pitches (2–3 paragraphs). Longer only for op-eds or background briefs.",
        "avoid": "Jargon, passive voice, generic org descriptions, anything that reads like marketing copy.",
        "sample_opener": "[Concrete fact or outcome] — [org] is doing [what], and [journalist's readers] will care because [why].",
    },
    "peer_colleague": {
        "label": "Peer / Sector Colleague",
        "formality": "Collegial and direct. First name always.",
        "opening_style": "Context-first: reference your connection or the shared context quickly.",
        "tone_notes": "Honest, collaborative, real. Sector insiders see through performance. Be yourself.",
        "length": "Appropriate to the ask. Short for intros and check-ins. Longer for collaboration asks.",
        "avoid": "Overly formal language, excessive politeness, anything that feels like a form letter.",
        "sample_opener": "Hi [name], I've been thinking about [topic/connection] and wanted to reach out — [brief direct ask or context].",
    },
    "consulting_client": {
        "label": "Crestline Collective Consulting Client",
        "formality": "Professional but personalized. Match the relationship register — formal if newer, collegial if established.",
        "opening_style": "Reference the engagement or project directly. Clients want to know you're on top of their work.",
        "tone_notes": "Trusted advisor tone: confident, clear, focused on their outcomes. Not deferential.",
        "length": "Appropriate to the deliverable. Brief for updates; full memos for strategy recommendations.",
        "avoid": "Generic consulting language, hedging, anything that sounds like a template.",
        "sample_opener": "Sharing [deliverable/update] for [project] — here's where things stand and what I recommend next.",
    },
}


class AudienceRegister(BaseTool):
    """
    Given an audience type, return the appropriate tone register, formality level,
    opening style, and drafting guidance for a communication.

    Use this at the start of any drafting task to set the right register before writing.
    The register profile anchors the draft and prevents defaulting to generic language.

    Combine with VoiceLibrary for full calibration on external communications.
    """

    audience_type: str = Field(
        ...,
        description=(
            "Audience type: 'major_donor', 'foundation_program_officer', 'board_member', "
            "'corporate_partner', 'community_member', 'government_official', 'media', "
            "'peer_colleague', or 'consulting_client'"
        ),
    )
    communication_type: str = Field(
        ...,
        description=(
            "What you're drafting: e.g., 'thank-you letter', 'cultivation email', "
            "'grant update', 'partnership pitch', 'LinkedIn post', 'op-ed', "
            "'board memo', 'event invitation', 'award nomination'"
        ),
    )
    org_context: str = Field(
        ...,
        description="Which org: 'LFLA' or 'Crestline'",
    )

    def run(self):
        normalized = self.audience_type.lower().replace(" ", "_").replace("-", "_")
        profile = AUDIENCE_PROFILES.get(normalized)

        if not profile:
            available = ", ".join(AUDIENCE_PROFILES.keys())
            return (
                f"Unknown audience type '{self.audience_type}'.\n"
                f"Available types: {available}"
            )

        org_note = (
            "LFLA — use LFLA signature, brand reference, and program language"
            if self.org_context == "LFLA"
            else "Crestline Collective — use Crestline Collective signature and treat deliverable as confidential"
        )

        lines = [
            f"## Audience Register: {profile['label']}",
            f"Communication type: {self.communication_type}",
            f"Org context: {self.org_context} ({org_note})\n",
            f"**Formality:** {profile['formality']}",
            f"**Opening style:** {profile['opening_style']}",
            f"**Tone notes:** {profile['tone_notes']}",
            f"**Recommended length:** {profile['length']}",
            f"**Avoid:** {profile['avoid']}",
            f"\n**Sample opener pattern:**\n  \"{profile['sample_opener']}\"",
            "\n---",
            "Apply this register to your draft. Use VoiceLibrary to further calibrate against Ellah's actual writing samples.",
        ]
        return "\n".join(lines)


if __name__ == "__main__":
    print("=== Test: Major donor thank-you ===")
    t1 = AudienceRegister(
        audience_type="major_donor",
        communication_type="thank-you letter",
        org_context="LFLA",
    )
    print(t1.run())

    print("\n=== Test: Foundation program officer grant update ===")
    t2 = AudienceRegister(
        audience_type="foundation_program_officer",
        communication_type="grant update",
        org_context="LFLA",
    )
    print(t2.run())

    print("\n=== Test: LinkedIn thought leadership post ===")
    t3 = AudienceRegister(
        audience_type="peer_colleague",
        communication_type="LinkedIn post",
        org_context="LFLA",
    )
    print(t3.run())
