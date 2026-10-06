# BAIT annotation codebook

This codebook defines the nine cognitive bias triggers annotated in BAIT.
Annotators worked from these entries. Each entry gives the category's
definition, the cognitive mechanism it draws on, its textual trigger signals,
a positive and a negative example, and notes on its boundary and on the
category it is most easily confused with. The examples were made up for
annotator training and do not come from the corpus.

## General rules

- **Reader's perspective.** A trigger is annotated on the basis of the textual
  cue a passage supplies, not on any inference about the author's intention.
- **Minimal span.** A span is the shortest contiguous fragment that, if
  removed, would eliminate the trigger. Annotators mark that fragment rather
  than the surrounding sentence or paragraph.
- **Multiple categories.** A single span may carry more than one trigger, in
  which case it is annotated once per applicable category.
- **Discontinuous triggers.** Spans of a single discontinuous trigger share a
  group identifier and form one trigger. Grouping only applies within one
  bias. In practice this mostly concerns B01 Illusory Truth, where the
  repetitions of a claim form one trigger.

## Annotation protocol

Each article was labelled independently by two annotators in two passes. The
first pass records, per category, whether the trigger occurs anywhere in the
article (`biases_present`). The second marks the minimal span or spans carrying
each present trigger, assigns its category, and records a confidence rating:

| Rating | Meaning | Inclusion in the gold standard |
|---|---|---|
| 3 | high | included automatically |
| 2 | moderate | included subject to adjudication |
| 1 | low | included only where adjudication confirmed it |

Annotators were told to give a lower rating rather than leave out a suspected
trigger, so that borderline cases reached adjudication. A third annotator
adjudicated every label into the released consensus set. The codebook was
frozen after two calibration rounds and did not change during annotation or
adjudication.

---

## B01 Illusory Truth

**Definition.** A claim is repeated two or more times within the article,
verbatim or in varied wording, such that repetition alone increases its
perceived truth value independent of evidential support.

**Mechanism.** Processing fluency. Text encountered before is processed more
easily, and that ease is misattributed as evidence of truth.

**Trigger signals.** Verbatim or near-verbatim repetition of a claim across
paragraphs; reformulated repetition of the same proposition; anaphoric cues
such as "as noted earlier" or "to repeat"; echoing of the same claim across
title, opening, and closing.

**Positive example.** "The new tax will devastate small businesses. Local
entrepreneurs warn that the policy will devastate small businesses across the
country. As mentioned, this measure threatens to destroy small business in our
communities."

**Negative example.** "The new tax will affect small businesses. According to a
2024 industry survey, 62% of business owners expect reduced margins, and 18%
anticipate closures within two years."

**Boundary and confusion.** Topical recurrence is not illusory truth. The
trigger requires the same propositional content to be asserted repeatedly, not
merely the same subject discussed from different angles. Most readily confused
with B02. B01 concerns repetition of any claim regardless of valence, whereas
B02 concerns asymmetric negative weighting.

## B02 Negativity Bias

**Definition.** Negative information (harm, threat, loss, failure) is
foregrounded, elaborated, or weighted more heavily than positive or neutral
information of comparable magnitude, biasing the reader's overall evaluation.

**Mechanism.** Negative valence captures attention disproportionately and is
encoded with greater perceptual and semantic detail than positive valence of
equal objective magnitude.

**Trigger signals.** Headline or lead foregrounding harm, loss, or threat;
asymmetric elaboration of negative outcomes with comparable positives omitted
or minimised; catastrophising vocabulary ("crisis", "disaster", "collapse",
"devastating"); loss-framed numerical reporting where gain framing was equally
available.

**Positive example.** "The economy shed 200,000 jobs last month in what experts
called a catastrophic collapse. Meanwhile, a modest 30,000 new positions were
added in tech."

**Negative example.** "The labour market lost 200,000 jobs in declining sectors
and added 30,000 in expanding ones, a net contraction of 170,000 positions."

**Boundary and confusion.** Reporting on a genuinely negative event is not in
itself a trigger. The trigger requires asymmetric elaboration or catastrophising
relative to what the facts support. Distinguished from B01 by asymmetric
weighting rather than repetition.

## B03 Bandwagon Effect

**Definition.** Claims are presented as believed or endorsed by a large or
growing majority, triggering the tendency to align one's own belief with
perceived social consensus.

**Mechanism.** Social proof. Majority adoption is treated as evidence of
correctness, independent of the underlying argument.

**Trigger signals.** Explicit majority appeal ("most people", "everyone knows",
"millions have already…"); viral or trending language; polling data framed to
emphasise consensus without methodological qualification; late-adoption shame
framing ("you haven't heard about this yet?").

**Positive example.** "Millions of parents have already switched to the new
formula. Are you still using the old one?"

**Negative example.** "A survey of 1,000 parents found that 60% preferred the
new formula, though the authors note the sample was not nationally
representative."

**Boundary and confusion.** Citing polling data is not itself a trigger. The
data must be framed to create social pressure or imply that deviating from the
majority is unreasonable. Most readily confused with B04. B03 invokes the crowd
and B04 a specific authority, and the two may co-occur in a single span.

## B04 Authority Bias

**Definition.** A claim is endorsed by or attributed to an authority figure or
institution in a way that substitutes for, rather than accompanies, evidential
support.

**Mechanism.** Source expertise, real or claimed, is used as a peripheral cue to
accept the message without scrutinising its content.

**Trigger signals.** Expert endorsement without cited evidence; credential
inflation ("leading scientist", "world-renowned expert"); institutional
authority invoked to close debate ("the science is settled"); irrelevant or
off-domain authority presented with impressive credentials.

**Positive example.** "Dr Helena Marsh, a leading nutrition expert, warns that
the chemical changes in the new formula are 'potentially devastating' for
children."

**Negative example.** "Dr Helena Marsh, who led the 2023 longitudinal study
published in The Lancet, reports that the modified compound was associated with
a 12% increase in adverse outcomes (n = 4,200, p < 0.01)."

**Boundary and confusion.** Quoting an expert is not itself a trigger. The
credential must substitute for the evidential basis the claim would otherwise
need. Distinguished from B03 by invoking a specific authority rather than the
crowd.

## B05 Stereotyping

**Definition.** A group is described as having fixed traits, dispositions, or
characteristics, with individual members presumed to share them by virtue of
group membership.

**Mechanism.** Prototype matching. A group label activates a fixed set of
attributed characteristics, and individual variation is suppressed.

**Trigger signals.** Generic group statements ("Women are…", "Immigrants tend
to…"); essentialist framing ("it's in their nature", "cultural DNA");
statistical generalisation applied at the individual level without hedging;
traits attributed to group membership rather than to circumstance or structure.

**Positive example.** "These migrants don't value education — it's a cultural
thing. That's why their children underperform."

**Negative example.** "Children from low-income households, regardless of
national or cultural background, face documented systemic barriers in
education, including under-resourced schools and reduced access to early-years
support."

**Boundary and confusion.** Properly hedged statistical claims ("on average",
"in this sample") are not stereotyping. The trigger is unqualified
generalisation or attribution of outcomes to group essence rather than to
structural conditions.

## B06 Declinism

**Definition.** The past is systematically presented as superior to the
present, framing current conditions as degraded, lost, or corrupted relative to
an idealised prior state.

**Mechanism.** The idealised past serves as an anchor, and the present is
evaluated against a selectively reconstructed, rosier baseline.

**Trigger signals.** Explicit nostalgia framing ("things were better when…");
asymmetric comparison in which past virtues are detailed and past problems
ignored; "golden age" language; restoration rhetoric ("return to", "reclaim
what was lost").

**Positive example.** "There was a time when this country worked. People had
real jobs, real communities, real values. Today we have nothing of the kind —
only decay where there was once dignity."

**Negative example.** "Manufacturing employment in the region fell from 38% in
1970 to 11% in 2023, while service-sector employment rose from 41% to 67% over
the same period."

**Boundary and confusion.** Acknowledging that something has worsened is not
itself declinism. The trigger requires the present to be framed as degraded
against an idealised past whose own problems are selectively omitted. Most
readily confused with B09. Declinism is an evaluative comparison (the past was
better), whereas hindsight is epistemic certainty (the outcome was
predictable).

## B07 Identifiable Victim Effect

**Definition.** A single, named, humanised victim produces a far stronger
emotional response and call to action than statistical descriptions of equal or
greater harm affecting anonymous populations.

**Mechanism.** Concrete, specific individuals activate empathy more powerfully
than statistical abstraction, so the identified life is weighted
disproportionately to the statistical one.

**Trigger signals.** A named victim with biographical detail (name, age,
family, backstory); first-person or direct-speech testimony of suffering;
explicit contrast between the individual and a statistic ("this is not a
number, this is Sarah"); emotional focus on one person while aggregate data is
absent or minimised.

**Positive example.** "Seven-year-old Emma loved football and drawing. Last
Tuesday, she died from a preventable disease. How many more Emmas must we
lose?"

**Negative example.** "The disease kills approximately 4,000 children annually
in this region. Emma's case, reported last week, reflects a pattern documented
across 23 countries."

**Boundary and confusion.** A personal story presented alongside statistical
context does not trigger the bias. The trigger is disproportionate or exclusive
use of the individual case to motivate a claim, with aggregate evidence
suppressed or absent.

## B08 Illusory Correlation

**Definition.** A text presents two events or variables as causally or
correlatively linked when the co-occurrence is coincidental, selective, or
logically insufficient to establish the claimed relationship.

**Mechanism.** Pattern detection overgeneralises. Distinctive co-occurrences are
weighted more heavily than their joint frequency warrants, and temporal
sequence is mistaken for causal mechanism.

**Trigger signals.** Post hoc reasoning ("after X, Y occurred, which is
why…"); juxtaposition of events with no stated mechanism; selective reporting
of only the co-occurring cases; correlation presented as causation without
mechanism, controls, or counterfactual.

**Positive example.** "The day after the new mayor took office, crime rose by
5%. His policies are already making the city less safe."

**Negative example.** "Crime statistics for the month following the new mayor's
inauguration showed a 5% increase. Criminologists note that month-to-month
fluctuations of this magnitude are typical and cannot be attributed to policies
implemented only days earlier."

**Boundary and confusion.** Not every temporal sequence is a trigger. The text
must present the sequence as evidence of a causal or systematic relationship
without sufficient justification. Most readily confused with B09. B08 is a
forward causal claim (cause → effect), B09 a backward claim of prior
predictability (outcome → "should have known").

## B09 Hindsight Bias

**Definition.** Knowing the outcome of an event, a text presents that outcome as
having been obvious or predictable beforehand, understating the genuine
uncertainty that existed at the time.

**Mechanism.** Outcome knowledge is projected backwards onto the prior state,
inflating perceived ex-ante predictability and erasing genuine epistemic
uncertainty.

**Trigger signals.** Phrases asserting prior obviousness ("it was always clear
that…", "anyone could have seen this coming", "it was inevitable");
retrospective certainty reconstructing events as foreordained; blame framing
dependent on post-hoc predictability ("they should have known"); selective
citation of early warnings while ignoring contemporary uncertainty.

**Positive example.** "It was obvious from the beginning that the policy would
fail. The warning signs were all there, and anyone paying attention could have
predicted this outcome."

**Negative example.** "Analysts were divided at the time of the policy's launch.
Some predicted success, citing X, and others warned of failure, citing Y. In
retrospect, the critics' concerns proved well-founded."

**Boundary and confusion.** Legitimate retrospective analysis that acknowledges
prior uncertainty is not hindsight bias. The trigger requires the outcome to be
presented as having been obviously predictable, erasing the genuine ex-ante
epistemic state. Distinguished from B06 by concerning certainty about a
specific outcome rather than idealisation of an era.
