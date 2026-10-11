# Valence feature reference

The caller encodes actions; Valence never infers features from titles or notes. The ontology is experimental. Encode effects and intensity, not utility or personality. All 19 keys are required. Values are dimensionless; duration is supplied separately in minutes. Rate features describe ongoing experience and produce utility/hour; one-time features describe the whole action's net outcome and produce utility once. Optional feature_duration_minutes overrides actual exposure for ongoing features only, between zero and action duration; omitted entries use the whole action duration. Brief episodes need not last for the whole event. Action net_money_cost is required separately: positive spending, negative income, zero for no monetary effect. Money uses one consistent caller-declared currency. The examples are anchors, not universal encodings of real-world activities.

## Mental effort (`mental_effort`)

Domain: [0, 1]. Response family: `cost`.

Ongoing experience: response in utility units/hour, multiplied by actual exposure duration.

Intensity of concentration, planning, decision-making, and working-memory demands during the activity, independently of rest or rewarding outcomes.

| Value | Anchor / example |
| --- | --- |
| 0 | No meaningful mental demand |
| 0.5 | Sustained moderate concentration |
| 1 | Extreme sustained mental effort |

Belongs: Concentration, planning, decision-making and working-memory demands.

Exclude: Mental rest; Curiosity engagement; Knowledge gained; Mastery satisfaction.

Distinction: Effort can coexist with curiosity, mastery, or relief; encode each independently rather than subtracting enjoyment from demand.

## Mental rest / relief (`mental_rest`)

Domain: [0, 1]. Response family: `reward`.

Ongoing experience: response in utility units/hour, multiplied by actual exposure duration.

Experienced mental rest, calm, decompression, or release from cognitive demands during the activity. This is relief and respite, not general enjoyment of thinking.

| Value | Anchor / example |
| --- | --- |
| 0 | No meaningful mental respite |
| 0.5 | Noticeable mental rest or decompression |
| 1 | Deep sustained mental rest or relief from demands |

Belongs: Mental rest, calm, decompression and respite from demands.

Exclude: Enjoyment of solving problems; Learning; Curiosity; Mastery; Post-action relief aftereffect.

Distinction: Low effort does not imply restorative rest. Mental rest describes respite actually experienced; other features capture rewards of active thought.

## Physical effort (`physical_effort`)

Domain: [0, 1]. Response family: `cost`.

Ongoing experience: response in utility units/hour, multiplied by actual exposure duration.

Intensity of bodily exertion, strain, discomfort, or fatigue during the activity, independently of pleasant bodily experience.

| Value | Anchor / example |
| --- | --- |
| 0 | No meaningful physical effort |
| 0.5 | Moderate bodily exertion |
| 1 | Extreme sustained physical effort |

Belongs: Exertion, strain, discomfort and fatigue during activity.

Exclude: Physical pleasure; Mental effort; Post-action fatigue amplitude.

Distinction: A demanding activity can also feel physically pleasant; encode effort and pleasure separately.

## Physical pleasure / comfort (`physical_pleasure`)

Domain: [0, 1]. Response family: `reward`.

Ongoing experience: response in utility units/hour, multiplied by actual exposure duration.

Intensity of pleasant bodily sensations, comfortable rest, or enjoyment of movement during the activity, independently of exertion.

| Value | Anchor / example |
| --- | --- |
| 0 | No meaningful physical pleasure or comfort |
| 0.5 | Noticeable pleasant movement or bodily comfort |
| 1 | Strong sustained bodily pleasure or comfort |

Belongs: Pleasant bodily sensations, comfortable rest and pleasant movement.

Exclude: Mastery; Recognition; Mental rest; Absence of effort alone.

Distinction: Pleasure and effort can both be high. A strenuous enjoyable run need not be encoded as either effort or pleasure alone.

## Stimulation / novelty (`stimulation_novelty`)

Domain: [0, 1]. Response family: `reward_overload`.

Ongoing experience: response in utility units/hour, multiplied by actual exposure duration.

Amount of novelty, excitement, sensory stimulation, unpredictability, and environmental intensity.

| Value | Anchor / example |
| --- | --- |
| 0 | Highly familiar or unstimulating |
| 0.5 | Noticeably novel or stimulating |
| 1 | Extremely novel or intense |

Belongs: Novelty, excitement, sensory stimulation and environmental intensity.

Exclude: Knowledge gained; Social contact quantity; Threat or safety change.

Distinction: Sensory novelty may teach little. Curiosity concerns inquiry; outcome uncertainty concerns uncertain consequences rather than excitement alone.

## Knowledge / learning gained (`learning_gain`)

Domain: [0, 1]. Response family: `reward`.

One-time outcome: counted once per action, in utility units.

Amount of meaningful new knowledge or understanding gained as a whole-action outcome, whether or not the learning process was engaging.

| Value | Anchor / example |
| --- | --- |
| 0 | No meaningful knowledge gained |
| 0.5 | Moderate substantive knowledge or understanding gained |
| 1 | Extensive substantive knowledge or understanding gained |

Belongs: New knowledge and understanding gained.

Exclude: Inquiry without learning; Mental effort; Sensory novelty; Mastery experience.

Distinction: Count the knowledge gained once. Curiosity engagement describes the inquiry experience and can occur without a useful discovery.

## Curiosity / exploration (`curiosity_engagement`)

Domain: [0, 1]. Response family: `reward`.

Ongoing experience: response in utility units/hour, multiplied by actual exposure duration.

Intensity of engaged inquiry, investigation, or exploration during the activity, independently of knowledge ultimately gained.

| Value | Anchor / example |
| --- | --- |
| 0 | No meaningful inquiry or exploration |
| 0.5 | Noticeably engaging investigation or exploration |
| 1 | Deep sustained engagement in inquiry or exploration |

Belongs: Engaged inquiry, investigation and exploration.

Exclude: Knowledge gained; Sensory novelty alone; Mental rest; Mastery alone.

Distinction: An investigation can engage curiosity without teaching anything new; mental effort can coexist with this experience.

## Autonomy / control (`autonomy_control`)

Domain: [-1, 1]. Response family: `asymmetric_signed`.

Ongoing experience: response in utility units/hour, multiplied by actual exposure duration.

Experienced freedom to choose, change, or refuse what one does during the activity versus coercion or imposed constraints. Existing freedom can be exercised without gaining future autonomy.

| Value | Anchor / example |
| --- | --- |
| -1 | Severely coerced with no meaningful choice |
| -0.5 | Meaningfully imposed or restrictive |
| 0 | No salient freedom or constraint |
| 0.5 | Meaningfully self-directed with real choices |
| 1 | Strong freedom to choose, change or refuse |

Belongs: Free choice, self-direction, personal control and coercion.

Exclude: Influence over other people or external events.

Distinction: A self-chosen detailed plan can have high structure and high autonomy. Influence concerns shaping external decisions rather than choosing one's own actions.

## Competence / mastery (`competence_mastery`)

Domain: [-1, 1]. Response family: `asymmetric_signed`.

Ongoing experience: response in utility units/hour, multiplied by actual exposure duration.

Expected experience of capability, mastery, successful challenge, or failure: effective skill use and overcoming challenge versus salient failure, helplessness, or inability to perform.

| Value | Anchor / example |
| --- | --- |
| -1 | Severe salient failure or inability to perform |
| -0.5 | Meaningful failure or helplessness |
| 0 | No salient capability experience |
| 0.5 | Successful challenge or effective skill use |
| 1 | Strong mastery experience |

Belongs: Successful challenge, skill use, mastery and salient failure.

Exclude: Knowledge gained; External recognition; Goal advancement alone.

Distinction: Do not duplicate learning. Mastery concerns experienced capability; recognition concerns others' praise or prestige.

## Goal progress (`goal_progress`)

Domain: [-1, 1]. Response family: `asymmetric_signed`.

One-time outcome: counted once per action, in utility units.

Expected net effect on relevant goals. The caller incorporates goal importance in the value; the Person Model determines the utility response to progress.

| Value | Anchor / example |
| --- | --- |
| -1 | Severe setback to an important goal |
| -0.5 | Meaningful setback |
| 0 | No meaningful effect |
| 0.5 | Meaningful progress |
| 1 | Major advancement of an important goal |

Belongs: Net advancement or setback, with relevant goal importance incorporated.

Exclude: Pleasure of progress itself; Ordinary liking; Completion alone.

Distinction: Goal advancement and structure are separate: progress may happen without making a plan more defined or predictable.

## Structure / planning (`structure_planning`)

Domain: [0, 1]. Response family: `order_preference`.

Ongoing experience: response in utility units/hour, multiplied by actual exposure duration.

Degree to which the activity follows a defined plan, rules, or sequence, independently of who chose it or how certain its outcomes are.

| Value | Anchor / example |
| --- | --- |
| 0 | Freely improvised without a defined sequence |
| 0.5 | Partly planned with room to improvise |
| 1 | Tightly planned or prescribed sequence |

Belongs: Defined plans, rules, routines and sequences.

Exclude: Freedom to choose or refuse; Certainty of outcomes; Goal progress.

Distinction: Structure does not determine autonomy or outcome certainty. A signed Person Model sensitivity can favor structure or improvisation.

## Outcome uncertainty (`outcome_uncertainty`)

Domain: [0, 1]. Response family: `order_preference`.

Ongoing experience: response in utility units/hour, multiplied by actual exposure duration.

Degree of uncertainty about relevant consequences given what the person knows, independently of planning, sensory novelty, or whether possible consequences are harmful.

| Value | Anchor / example |
| --- | --- |
| 0 | Relevant consequences are predictable |
| 0.5 | Meaningfully uncertain relevant consequences |
| 1 | Widely varying possible relevant consequences |

Belongs: Uncertainty about relevant outcomes.

Exclude: Lack of planning alone; Sensory surprise alone; Expected money loss; Harm or moral violation alone.

Distinction: A planned event can have uncertain outcomes. Uncertainty is not downside risk: encode gains and losses in the relevant outcome or resource fields without counting them here again.

## Social exposure (`social_exposure`)

Domain: [0, 1]. Response family: `reward_overload`.

Ongoing experience: response in utility units/hour, multiplied by actual exposure duration.

Quantity and intensity of interpersonal interaction, independent of whether the person likes socializing.

| Value | Anchor / example |
| --- | --- |
| 0 | Solitary |
| 0.25 | Light interaction |
| 0.5 | Sustained interaction with a few people |
| 0.75 | Socially intensive group activity |
| 1 | Extremely socially intensive interaction |

Belongs: Amount and intensity of interpersonal interaction.

Exclude: Whether socializing is liked; Closeness; Acceptance; Prestige.

Distinction: Contact intensity differs from meaningful closeness, group inclusion and status; these have separate signed features.

## Relatedness / intimacy (`relatedness_intimacy`)

Domain: [-1, 1]. Response family: `asymmetric_signed`.

Ongoing experience: response in utility units/hour, multiplied by actual exposure duration.

Experienced meaningful warmth, closeness, intimacy, or relational conflict during the activity. Existing closeness can be enjoyed without a lasting relationship improvement.

| Value | Anchor / example |
| --- | --- |
| -1 | Severe experienced conflict or disconnection |
| -0.5 | Meaningful relational tension |
| 0 | No salient closeness or conflict |
| 0.5 | Meaningful warmth or connection |
| 1 | Strong experienced intimacy or closeness |

Belongs: Experienced intimacy, relational warmth, conflict and disconnection.

Exclude: Generic social interaction; Group inclusion alone; Lasting relationship change alone.

Distinction: Generic interaction belongs in social_exposure; belonging_acceptance concerns inclusion or rejection rather than intimate closeness.

## Belonging / acceptance (`belonging_acceptance`)

Domain: [-1, 1]. Response family: `asymmetric_signed`.

Ongoing experience: response in utility units/hour, multiplied by actual exposure duration.

Experienced membership, inclusion, welcome, acceptance, rejection, or exclusion during the activity. Belonging to an existing group does not require newly earning acceptance.

| Value | Anchor / example |
| --- | --- |
| -1 | Severe rejection or exclusion |
| -0.5 | Meaningful social disapproval or exclusion |
| 0 | No meaningful inclusion effect |
| 0.5 | Meaningfully welcomed or included |
| 1 | Strong acceptance and belonging |

Belongs: Inclusion, welcome, acceptance, rejection and exclusion.

Exclude: Prestige or praise alone; Intimacy alone; Quantity of interaction.

Distinction: Acceptance concerns inclusion; status_recognition concerns prestige. Inclusion need not imply intimacy or admiration.

## Status / recognition (`status_recognition`)

Domain: [-1, 1]. Response family: `asymmetric_signed`.

One-time outcome: counted once per action, in utility units.

Whole-action recognition episode: being admired, respected, acknowledged, dismissed, or humiliated, including recognition of existing status. A lasting reputation gain is not required.

| Value | Anchor / example |
| --- | --- |
| -1 | Severe humiliation or dismissal |
| -0.5 | Meaningful loss of face |
| 0 | No meaningful recognition episode |
| 0.5 | Meaningful admiration or recognition |
| 1 | Strong admiration, respect or acknowledgment |

Belongs: Praise, prestige, reputation, humiliation and loss of face.

Exclude: Inclusion alone; Capability alone; Decision authority alone.

Distinction: Recognition is external regard; competence_mastery is capability experienced, and influence_power is ability to shape external outcomes.

## Influence / power (`influence_power`)

Domain: [-1, 1]. Response family: `asymmetric_signed`.

Ongoing experience: response in utility units/hour, multiplied by actual exposure duration.

Experienced exercise of authority, leadership, or a meaningful say in external decisions during the activity versus being overruled or powerless. Existing influence can be exercised without gaining permanent power.

| Value | Anchor / example |
| --- | --- |
| -1 | Severely overruled or powerless over relevant decisions |
| -0.5 | Meaningfully denied a say |
| 0 | No salient exercise or denial of influence |
| 0.5 | Meaningful say or leadership |
| 1 | Strong exercise of authority or direction followed by others |

Belongs: Leadership and influence over external people, resources or decisions.

Exclude: Control over one's own actions; Prestige alone; Personal skill success alone.

Distinction: Autonomy concerns control over one's own actions; influence concerns external people or events, even without prestige.

## Contribution / care (`contribution_care`)

Domain: [-1, 1]. Response family: `asymmetric_signed`.

One-time outcome: counted once per action, in utility units.

Effect on helping, protecting, caring for, benefiting, or harming others: meaningful contribution or improved welfare versus meaningful avoidable harm or neglect of an important responsibility.

| Value | Anchor / example |
| --- | --- |
| -1 | Severe avoidable harm or neglect |
| -0.5 | Meaningful harm to others |
| 0 | No meaningful welfare effect on others |
| 0.5 | Meaningful help or care |
| 1 | Major benefit or protection for others |

Belongs: Helping, protection, care, others' welfare and avoidable harm.

Exclude: Recognition for helping; Personal liking; Value alignment alone.

Distinction: Contribution records others' welfare; identity_value_alignment records expressing or violating one's ideals. These can differ.

## Personal principles / values (`identity_value_alignment`)

Domain: [-1, 1]. Response family: `asymmetric_signed`.

Ongoing experience: response in utility units/hour, multiplied by actual exposure duration.

Expression or violation of specific personal principles during the activity, such as honesty, fairness, or a concrete commitment. Encode the principle at stake rather than general liking, ego, or desired self-image.

| Value | Anchor / example |
| --- | --- |
| -1 | Substantial violation of an identified personal principle |
| -0.5 | Meaningful conflict with a specific principle |
| 0 | No specific principle expressed or violated |
| 0.5 | Meaningfully expresses a specific principle |
| 1 | Strong expression of an important personal principle |

Belongs: Expression or violation of identified personal principles.

Exclude: Broad desired self-image; Ego or prestige alone; Ordinary preferences; Others' welfare alone; Goal advancement alone.

Distinction: Keep the specific principle distinct from mastery, recognition, contribution, and liking. An unpleasant action can still express honesty or fairness.
