"""Canonical public action-vector specification. Values describe the action, not liking."""


def _feature(key, name, minimum, definition, anchors, belongs, excludes, distinction, family):
    return {
        "key": key, "display_name": name, "minimum": minimum, "maximum": 1.0,
        "definition": definition, "anchors": [{"value": x, "description": d} for x, d in anchors],
        "belongs": belongs, "excludes": excludes, "distinction": distinction,
        "response_family": family,
        "temporal_basis": "one_time" if key in ONE_TIME_FEATURES else "rate",
        "examples": [{"value": x, "description": d} for x, d in anchors],
    }


SIGNED = "asymmetric_signed"
# Net outcomes are encoded for the entire action. Experienced qualities remain
# rates, including experienced capability and value alignment during activity.
ONE_TIME_FEATURES = frozenset({
    "learning_gain", "goal_progress", "status_recognition", "contribution_care",
})
ONTOLOGY = [
    _feature("mental_effort", "Mental effort", 0.0,
             "Intensity of concentration, planning, decision-making, and working-memory demands during the activity, independently of rest or rewarding outcomes.",
             [(0, "No meaningful mental demand"), (.5, "Sustained moderate concentration"), (1, "Extreme sustained mental effort")],
             ["Concentration, planning, decision-making and working-memory demands"], ["Mental rest", "Curiosity engagement", "Knowledge gained", "Mastery satisfaction"],
             "Effort can coexist with curiosity, mastery, or relief; encode each independently rather than subtracting enjoyment from demand.", "cost"),
    _feature("mental_rest", "Mental rest / relief", 0.0,
             "Experienced mental rest, calm, decompression, or release from cognitive demands during the activity. This is relief and respite, not general enjoyment of thinking.",
             [(0, "No meaningful mental respite"), (.5, "Noticeable mental rest or decompression"), (1, "Deep sustained mental rest or relief from demands")],
             ["Mental rest, calm, decompression and respite from demands"], ["Enjoyment of solving problems", "Learning", "Curiosity", "Mastery", "Post-action relief aftereffect"],
             "Low effort does not imply restorative rest. Mental rest describes respite actually experienced; other features capture rewards of active thought.", "reward"),
    _feature("physical_effort", "Physical effort", 0.0,
             "Intensity of bodily exertion, strain, discomfort, or fatigue during the activity, independently of pleasant bodily experience.",
             [(0, "No meaningful physical effort"), (.5, "Moderate bodily exertion"), (1, "Extreme sustained physical effort")],
             ["Exertion, strain, discomfort and fatigue during activity"], ["Physical pleasure", "Mental effort", "Post-action fatigue amplitude"],
             "A demanding activity can also feel physically pleasant; encode effort and pleasure separately.", "cost"),
    _feature("physical_pleasure", "Physical pleasure / comfort", 0.0,
             "Intensity of pleasant bodily sensations, comfortable rest, or enjoyment of movement during the activity, independently of exertion.",
             [(0, "No meaningful physical pleasure or comfort"), (.5, "Noticeable pleasant movement or bodily comfort"), (1, "Strong sustained bodily pleasure or comfort")],
             ["Pleasant bodily sensations, comfortable rest and pleasant movement"], ["Mastery", "Recognition", "Mental rest", "Absence of effort alone"],
             "Pleasure and effort can both be high. A strenuous enjoyable run need not be encoded as either effort or pleasure alone.", "reward"),
    _feature("stimulation_novelty", "Stimulation / novelty", 0.0,
             "Amount of novelty, excitement, sensory stimulation, unpredictability, and environmental intensity.",
             [(0, "Highly familiar or unstimulating"), (.5, "Noticeably novel or stimulating"), (1, "Extremely novel or intense")],
             ["Novelty, excitement, sensory stimulation and environmental intensity"], ["Knowledge gained", "Social contact quantity", "Threat or safety change"],
             "Sensory novelty may teach little. Curiosity concerns inquiry; outcome uncertainty concerns uncertain consequences rather than excitement alone.", "reward_overload"),
    _feature("learning_gain", "Knowledge / learning gained", 0.0,
             "Amount of meaningful new knowledge or understanding gained as a whole-action outcome, whether or not the learning process was engaging.",
             [(0, "No meaningful knowledge gained"), (.5, "Moderate substantive knowledge or understanding gained"), (1, "Extensive substantive knowledge or understanding gained")],
             ["New knowledge and understanding gained"], ["Inquiry without learning", "Mental effort", "Sensory novelty", "Mastery experience"],
             "Count the knowledge gained once. Curiosity engagement describes the inquiry experience and can occur without a useful discovery.", "reward"),
    _feature("curiosity_engagement", "Curiosity / exploration", 0.0,
             "Intensity of engaged inquiry, investigation, or exploration during the activity, independently of knowledge ultimately gained.",
             [(0, "No meaningful inquiry or exploration"), (.5, "Noticeably engaging investigation or exploration"), (1, "Deep sustained engagement in inquiry or exploration")],
             ["Engaged inquiry, investigation and exploration"], ["Knowledge gained", "Sensory novelty alone", "Mental rest", "Mastery alone"],
             "An investigation can engage curiosity without teaching anything new; mental effort can coexist with this experience.", "reward"),
    _feature("autonomy_control", "Autonomy / control", -1.0,
             "Experienced freedom to choose, change, or refuse what one does during the activity versus coercion or imposed constraints. Existing freedom can be exercised without gaining future autonomy.",
             [(-1, "Severely coerced with no meaningful choice"), (-.5, "Meaningfully imposed or restrictive"), (0, "No salient freedom or constraint"), (.5, "Meaningfully self-directed with real choices"), (1, "Strong freedom to choose, change or refuse")],
             ["Free choice, self-direction, personal control and coercion"], ["Influence over other people or external events"],
             "A self-chosen detailed plan can have high structure and high autonomy. Influence concerns shaping external decisions rather than choosing one's own actions.", SIGNED),
    _feature("competence_mastery", "Competence / mastery", -1.0,
             "Expected experience of capability, mastery, successful challenge, or failure: effective skill use and overcoming challenge versus salient failure, helplessness, or inability to perform.",
             [(-1, "Severe salient failure or inability to perform"), (-.5, "Meaningful failure or helplessness"), (0, "No salient capability experience"), (.5, "Successful challenge or effective skill use"), (1, "Strong mastery experience")],
             ["Successful challenge, skill use, mastery and salient failure"], ["Knowledge gained", "External recognition", "Goal advancement alone"],
             "Do not duplicate learning. Mastery concerns experienced capability; recognition concerns others' praise or prestige.", SIGNED),
    _feature("goal_progress", "Goal progress", -1.0,
             "Expected net effect on relevant goals. The caller incorporates goal importance in the value; the Person Model determines the utility response to progress.",
             [(-1, "Severe setback to an important goal"), (-.5, "Meaningful setback"), (0, "No meaningful effect"), (.5, "Meaningful progress"), (1, "Major advancement of an important goal")],
             ["Net advancement or setback, with relevant goal importance incorporated"], ["Pleasure of progress itself", "Ordinary liking", "Completion alone"],
             "Goal advancement and structure are separate: progress may happen without making a plan more defined or predictable.", SIGNED),
    _feature("structure_planning", "Structure / planning", 0.0,
             "Degree to which the activity follows a defined plan, rules, or sequence, independently of who chose it or how certain its outcomes are.",
             [(0, "Freely improvised without a defined sequence"), (.5, "Partly planned with room to improvise"), (1, "Tightly planned or prescribed sequence")],
             ["Defined plans, rules, routines and sequences"], ["Freedom to choose or refuse", "Certainty of outcomes", "Goal progress"],
             "Structure does not determine autonomy or outcome certainty. A signed Person Model sensitivity can favor structure or improvisation.", "order_preference"),
    _feature("outcome_uncertainty", "Outcome uncertainty", 0.0,
             "Degree of uncertainty about relevant consequences given what the person knows, independently of planning, sensory novelty, or whether possible consequences are harmful.",
             [(0, "Relevant consequences are predictable"), (.5, "Meaningfully uncertain relevant consequences"), (1, "Widely varying possible relevant consequences")],
             ["Uncertainty about relevant outcomes"], ["Lack of planning alone", "Sensory surprise alone", "Expected money loss", "Harm or moral violation alone"],
             "A planned event can have uncertain outcomes. Uncertainty is not downside risk: encode gains and losses in the relevant outcome or resource fields without counting them here again.", "order_preference"),
    _feature("social_exposure", "Social exposure", 0.0,
             "Quantity and intensity of interpersonal interaction, independent of whether the person likes socializing.",
             [(0, "Solitary"), (.25, "Light interaction"), (.5, "Sustained interaction with a few people"), (.75, "Socially intensive group activity"), (1, "Extremely socially intensive interaction")],
             ["Amount and intensity of interpersonal interaction"], ["Whether socializing is liked", "Closeness", "Acceptance", "Prestige"],
             "Contact intensity differs from meaningful closeness, group inclusion and status; these have separate signed features.", "reward_overload"),
    _feature("relatedness_intimacy", "Relatedness / intimacy", -1.0,
             "Experienced meaningful warmth, closeness, intimacy, or relational conflict during the activity. Existing closeness can be enjoyed without a lasting relationship improvement.",
             [(-1, "Severe experienced conflict or disconnection"), (-.5, "Meaningful relational tension"), (0, "No salient closeness or conflict"), (.5, "Meaningful warmth or connection"), (1, "Strong experienced intimacy or closeness")],
             ["Experienced intimacy, relational warmth, conflict and disconnection"], ["Generic social interaction", "Group inclusion alone", "Lasting relationship change alone"],
             "Generic interaction belongs in social_exposure; belonging_acceptance concerns inclusion or rejection rather than intimate closeness.", SIGNED),
    _feature("belonging_acceptance", "Belonging / acceptance", -1.0,
             "Experienced membership, inclusion, welcome, acceptance, rejection, or exclusion during the activity. Belonging to an existing group does not require newly earning acceptance.",
             [(-1, "Severe rejection or exclusion"), (-.5, "Meaningful social disapproval or exclusion"), (0, "No meaningful inclusion effect"), (.5, "Meaningfully welcomed or included"), (1, "Strong acceptance and belonging")],
             ["Inclusion, welcome, acceptance, rejection and exclusion"], ["Prestige or praise alone", "Intimacy alone", "Quantity of interaction"],
             "Acceptance concerns inclusion; status_recognition concerns prestige. Inclusion need not imply intimacy or admiration.", SIGNED),
    _feature("status_recognition", "Status / recognition", -1.0,
             "Whole-action recognition episode: being admired, respected, acknowledged, dismissed, or humiliated, including recognition of existing status. A lasting reputation gain is not required.",
             [(-1, "Severe humiliation or dismissal"), (-.5, "Meaningful loss of face"), (0, "No meaningful recognition episode"), (.5, "Meaningful admiration or recognition"), (1, "Strong admiration, respect or acknowledgment")],
             ["Praise, prestige, reputation, humiliation and loss of face"], ["Inclusion alone", "Capability alone", "Decision authority alone"],
             "Recognition is external regard; competence_mastery is capability experienced, and influence_power is ability to shape external outcomes.", SIGNED),
    _feature("influence_power", "Influence / power", -1.0,
             "Experienced exercise of authority, leadership, or a meaningful say in external decisions during the activity versus being overruled or powerless. Existing influence can be exercised without gaining permanent power.",
             [(-1, "Severely overruled or powerless over relevant decisions"), (-.5, "Meaningfully denied a say"), (0, "No salient exercise or denial of influence"), (.5, "Meaningful say or leadership"), (1, "Strong exercise of authority or direction followed by others")],
             ["Leadership and influence over external people, resources or decisions"], ["Control over one's own actions", "Prestige alone", "Personal skill success alone"],
             "Autonomy concerns control over one's own actions; influence concerns external people or events, even without prestige.", SIGNED),
    _feature("contribution_care", "Contribution / care", -1.0,
             "Effect on helping, protecting, caring for, benefiting, or harming others: meaningful contribution or improved welfare versus meaningful avoidable harm or neglect of an important responsibility.",
             [(-1, "Severe avoidable harm or neglect"), (-.5, "Meaningful harm to others"), (0, "No meaningful welfare effect on others"), (.5, "Meaningful help or care"), (1, "Major benefit or protection for others")],
             ["Helping, protection, care, others' welfare and avoidable harm"], ["Recognition for helping", "Personal liking", "Value alignment alone"],
             "Contribution records others' welfare; identity_value_alignment records expressing or violating one's ideals. These can differ.", SIGNED),
    _feature("identity_value_alignment", "Personal principles / values", -1.0,
             "Expression or violation of specific personal principles during the activity, such as honesty, fairness, or a concrete commitment. Encode the principle at stake rather than general liking, ego, or desired self-image.",
             [(-1, "Substantial violation of an identified personal principle"), (-.5, "Meaningful conflict with a specific principle"), (0, "No specific principle expressed or violated"), (.5, "Meaningfully expresses a specific principle"), (1, "Strong expression of an important personal principle")],
             ["Expression or violation of identified personal principles"], ["Broad desired self-image", "Ego or prestige alone", "Ordinary preferences", "Others' welfare alone", "Goal advancement alone"],
             "Keep the specific principle distinct from mastery, recognition, contribution, and liking. An unpleasant action can still express honesty or fairness.", SIGNED),
]

FEATURE_KEYS = tuple(item["key"] for item in ONTOLOGY)
FEATURE_BY_KEY = {item["key"]: item for item in ONTOLOGY}


def render_markdown():
    """Generate the external caller guide from the same specification exposed by the API."""
    lines = ["# Valence feature reference", "", f"The caller encodes actions; Valence never infers features from titles or notes. The ontology is experimental. Encode effects and intensity, not utility or personality. All {len(FEATURE_KEYS)} keys are required. Values are dimensionless; duration is supplied separately in minutes. Rate features describe ongoing experience and produce utility/hour; one-time features describe the whole action's net outcome and produce utility once. Optional feature_duration_minutes overrides actual exposure for ongoing features only, between zero and action duration; omitted entries use the whole action duration. Brief episodes need not last for the whole event. Action net_money_cost is required separately: positive spending, negative income, zero for no monetary effect. Money uses one consistent caller-declared currency. The examples are anchors, not universal encodings of real-world activities.", ""]
    for item in ONTOLOGY:
        basis = "One-time outcome: counted once per action, in utility units." if item["temporal_basis"] == "one_time" else "Ongoing experience: response in utility units/hour, multiplied by actual exposure duration."
        lines.extend([f"## {item['display_name']} (`{item['key']}`)", "", f"Domain: [{item['minimum']:g}, {item['maximum']:g}]. Response family: `{item['response_family']}`.", "", basis, "", item["definition"], "", "| Value | Anchor / example |", "| --- | --- |"])
        lines.extend(f"| {a['value']:g} | {a['description']} |" for a in item["anchors"])
        lines.extend(["", "Belongs: " + "; ".join(item["belongs"]) + ".", "", "Exclude: " + "; ".join(item["excludes"]) + ".", "", "Distinction: " + item["distinction"], ""])
    return "\n".join(lines)


if __name__ == "__main__":
    from pathlib import Path
    Path(__file__).resolve().parents[3].joinpath("FEATURES.md").write_text(render_markdown(), encoding="utf-8")
