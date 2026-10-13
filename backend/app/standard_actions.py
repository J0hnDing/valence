"""Manually encoded starter actions, independent of any person's preferences."""

from app.core.ontology import FEATURE_KEYS
from app.schemas import ActionInput


def standard_actions():
    """Return editable assumptions, not universal encodings or inferred outcomes."""
    definitions = [
        ("Eat a meal", 30, {
            "mental_rest": (.2, "A relaxed meal with a short break from work."),
            "physical_pleasure": (.4, "Assumes enjoyable taste and bodily comfort; hunger relief is not modeled."),
        }),
        ("Sleep", 480, {
            "mental_rest": (.8, "An eight-hour restful sleep, represented only as release from demands. Sleep need and subsequent energy recovery are not modeled."),
        }),
        ("Play League of Legends", 60, {
            "mental_effort": (.6, "Sustained attention, tactical decisions, and coordination during a match."),
            "stimulation_novelty": (.65, "Fast-changing gameplay and frequent stimulation."),
            "autonomy_control": (.4, "Voluntarily chosen play, with some constraints once a match starts."),
            "competence_mastery": (.2, "Moderately successful skill use; does not assume winning."),
            "structure_planning": (.7, "Defined game rules and objectives, with tactical improvisation."),
            "outcome_uncertainty": (.7, "Match results and teammate behavior are uncertain."),
            "social_exposure": (.3, "Light online interaction with teammates; no friendship or acceptance assumed."),
        }),
        ("Study", 60, {
            "mental_effort": (.7, "Focused reading, recall, and practice."),
            "stimulation_novelty": (.25, "Some new material in an otherwise familiar study routine."),
            "learning_gain": (.5, "A moderate whole-session learning gain, not a gain per hour."),
            "curiosity_engagement": (.3, "Some active interest in understanding the material."),
            "autonomy_control": (.4, "Choice of study approach within assigned material."),
            "competence_mastery": (.2, "Some successful understanding and problem solving."),
            "goal_progress": (.35, "Assumes this session advances a relevant academic goal; adjust for the actual goal."),
            "structure_planning": (.6, "A study plan with defined material and exercises."),
        }),
        ("Go for a walk", 30, {
            "mental_rest": (.5, "A relaxed solo walk away from demanding tasks."),
            "physical_effort": (.25, "An easy-to-moderate walking pace."),
            "physical_pleasure": (.3, "Assumes comfortable movement and surroundings."),
            "stimulation_novelty": (.2, "Mild environmental variety on a familiar route."),
            "autonomy_control": (.5, "Free choice of route and pace."),
        }),
        ("Watch a movie", 120, {
            "mental_effort": (.1, "Light attention to following the story."),
            "mental_rest": (.45, "A leisure break from work and responsibilities."),
            "stimulation_novelty": (.5, "A new movie with moderate audiovisual stimulation."),
            "curiosity_engagement": (.25, "Interest in the story and what happens next."),
            "autonomy_control": (.4, "A voluntarily chosen movie watched alone at home."),
            "structure_planning": (.3, "Following a fixed narrative with little planning required."),
        }),
        ("Build a project", 120, {
            "mental_effort": (.65, "Focused design, implementation, and troubleshooting."),
            "stimulation_novelty": (.35, "Some new problems and approaches."),
            "learning_gain": (.35, "A moderate whole-session gain in practical knowledge."),
            "curiosity_engagement": (.5, "Active exploration of how to make the project work."),
            "autonomy_control": (.7, "A self-directed personal project."),
            "competence_mastery": (.4, "Assumes useful, moderately successful implementation."),
            "goal_progress": (.5, "Assumes concrete progress on a relevant project goal, counted once."),
            "structure_planning": (.4, "A rough plan with room to explore."),
            "outcome_uncertainty": (.3, "Some uncertainty about whether the approach will work."),
        }),
        ("Exercise", 45, {
            "mental_effort": (.15, "Attention to technique and the workout sequence."),
            "physical_effort": (.65, "A moderately demanding workout."),
            "physical_pleasure": (.25, "Some rewarding bodily sensation alongside effort."),
            "autonomy_control": (.4, "A voluntarily chosen solo workout."),
            "competence_mastery": (.2, "Successful completion of familiar exercises."),
            "structure_planning": (.6, "A planned workout routine."),
        }),
        ("Read a book", 45, {
            "mental_effort": (.2, "Light-to-moderate attention to leisure reading."),
            "mental_rest": (.35, "A quiet break from other demands."),
            "stimulation_novelty": (.25, "Some new ideas or narrative developments."),
            "curiosity_engagement": (.4, "Interest in the subject or story; no specific learning outcome assumed."),
            "autonomy_control": (.5, "Freely chosen reading at one's own pace."),
        }),
        ("Cook a meal", 45, {
            "mental_effort": (.3, "Following a recipe and coordinating preparation."),
            "physical_effort": (.2, "Light standing, chopping, and kitchen movement."),
            "stimulation_novelty": (.2, "Some sensory variety in familiar cooking."),
            "autonomy_control": (.5, "Choice of meal and preparation method."),
            "competence_mastery": (.3, "Assumes successful preparation of a familiar meal."),
            "structure_planning": (.6, "A recipe or defined sequence. Eating is a separate action."),
        }),
        ("Do household chores", 30, {
            "mental_effort": (.1, "Simple routine tasks."),
            "physical_effort": (.3, "Light-to-moderate cleaning and tidying."),
            "autonomy_control": (.2, "Some choice of order and method within necessary chores."),
            "competence_mastery": (.15, "Successfully completing familiar household tasks."),
            "structure_planning": (.5, "A short list of routine tasks."),
        }),
        ("Spend time with friends", 60, {
            "mental_effort": (.15, "Light conversational attention."),
            "mental_rest": (.3, "A casual social break from work."),
            "stimulation_novelty": (.3, "Varied conversation in a familiar setting."),
            "autonomy_control": (.5, "Voluntary time together with flexible plans."),
            "social_exposure": (.6, "Sustained interaction with a few friends."),
            "relatedness_intimacy": (.5, "Assumes warm, supportive existing friendships."),
            "belonging_acceptance": (.4, "Assumes feeling welcome and included."),
        }),
    ]
    baseline = "Starter assumption: no salient effect in this scenario. Review for your context; values describe the action, not personal liking."
    for title, duration, encoded in definitions:
        features = {key: 0.0 for key in FEATURE_KEYS}
        notes = {key: baseline for key in FEATURE_KEYS}
        for key, (value, rationale) in encoded.items():
            features[key] = value
            notes[key] = "Starter assumption: " + rationale
        yield ActionInput(title=title, duration_minutes=duration, net_money_cost=0,
                          features=features, feature_notes=notes)
