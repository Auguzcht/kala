> Archived: 2026-10-24 (Asia/Manila), under APPROVAL-01. Historical source: `docs/audits/2026-10-18-bank-lesson-audit.md` at base `e9de105`.
> Replacement: [docs/work/handover-2026/evidence/migration-map.md](<../../work/handover-2026/evidence/migration-map.md>). This original is evidence, not current policy; old commands and next-step queues are not authorization to execute them. Source line references below and in audits refer to the original, before this header.

# Bank and lesson quality audit — 2026-10-18

Snapshot: 2026-10-18T03:07:42.883305+08:00 (initial SELECTs; referenced-check reads followed). Database: linked live project jcufmpxjlgdfzefvulvz. Read-only REST selects through app.db; no RPC, lesson assembly, API routes, database writes, or generation calls. Pagination: stable id order, 200 rows per page. Reads are not a transactionally consistent snapshot.

## A1. Broken answer keys — checked first

Active origin=bank items: **193**; broken keys/choice counts: **0**. Criteria: answer id absent from choices, or fewer than two choices. Severity: a confirmed inaccessible answer key would be high severity (study and grading); none found in this snapshot. No claim that the reported UI symptom is resolved.

| Course | Skill | Bank items | Broken |
| --- | --- | --- | --- |
| ae4e7680 | 3b4046cf Compare and contrast traditional IT infrastructure with cloud computing models | 20 | 0 |
| ae4e7680 | 3ef47b2f Describe the six benefits of cloud computing and the six perspectives of the AWS Cloud Adoption Framework (AWS CAF) | 20 | 0 |
| ae4e7680 | 52828069 Explain AWS scalability, elasticity, and high availability principles | 20 | 0 |
| ae4e7680 | 7e3656fb Select appropriate AWS compute, storage, and database services for a given workload requirement | 20 | 0 |
| ae4e7680 | 910b1f7d Compare managed AWS services against self-managed alternatives based on operational and cost trade-offs | 12 | 0 |
| ae4e7680 | d678c6ee Identify core AWS service categories and their primary use cases | 20 | 0 |
| ae4e7680 | df7207ee Identify the purpose and primary use cases of core AWS compute, storage, and database services | 21 | 0 |
| ae4e7680 | e269882f Define cloud computing and its essential characteristics | 12 | 0 |
| ae4e7680 | eed94898 Identify appropriate AWS service categories (compute, storage, database, networking) for given business requirements | 48 | 0 |

| Course | Bank items | Broken |
| --- | --- | --- |
| 4f14665c | 0 | 0 |
| 5a34472f | 0 | 0 |
| 6b83b489 | 0 | 0 |
| ade5c095 | 0 | 0 |
| ae4e7680 | 193 | 0 |

Broken-item saved answers: 0; marked correct=true: 0. With no broken items this is an empty cohort, not evidence of an ungradeable card.

| Item | Prompt (80) | Choice ids | Answer id | Created | Answers / correct |
| --- | --- | --- | --- | --- | --- |

### Reported CAF card and root-cause assessment

All matching 'six perspectives' rows are listed below as a supplemental legacy check. The exact reported prompt does not occur in the active bank cohort. Current worker code validates ids a–d and key membership (`services/worker/app/item_gen.py:157–176`). Bank validation calls it at `services/worker/app/jobs/bank_build.py:265`, then shuffles complete choice dictionaries at lines 515–516 and persists the unchanged answer id at line 517. Shuffling changes order, not ids or labels, so it does not explain a dangling answer key. Legacy async generation persists validated choices and key at `services/worker/app/item_gen.py:290–305`. Historical creator for an individual row is NOT CONFIRMED: origin/version do not identify the exact executed source revision. No reproduction of this UI symptom was attempted.

`correct_label` returns a matching label or None (`services/api/app/learn/items.py:450–466`). Study responses also fall back to a null label when the back query misses a row (`services/api/app/routers/flashcards.py:324–339`, `:390–401`). Thus a displayed null does not by itself prove a corrupt bank key. Root cause of the reported null is **NOT CONFIRMED**; no unsupported shuffle bug is asserted.

| Item | Origin | Retired | Key | Resolved label |
| --- | --- | --- | --- | --- |
| a6ef6252 | legacy | not retired | a | Business, People, Governance, Platform, Security, Operations |
| 880b0118 | legacy | not retired | a | Business, People, Governance, Platform, Security, and Operations |
| 9973edc4 | legacy | not retired | a | Business, People, Governance, Platform, Security, and Operations |
| dba6331f | legacy | not retired | c | Marketing |
| a05ec865 | legacy | not retired | b | Business, People, Governance, Platform, Security, Operations |
| 7266610a | legacy | not retired | a | Business, People, Governance, Platform, Security, and Operations |
| ad4bd4bd | legacy | not retired | a | Benefits: Trade capital expense for variable expense, benefit from massive economies of scale, stop guessing capacity, increase speed and agility, stop spending money running and maintaining data centers, go global in minutes. AWS CAF perspectives: Business, People, Governance, Platform, Security, Operations. |
| 56f7a56b | legacy | not retired | a | Business, People, Governance, Platform, Security, and Operations |
| dbe66e80 | legacy | not retired | a | Business, People, Governance, Platform, Security, Operations |
| 19168005 | legacy | not retired | a | Business, People, Governance, Platform, Security, and Operations |
| 73806ef7 | legacy | not retired | a | Business, People, Governance, Platform, Security, and Operations |
| 64b287a0 | legacy | not retired | a | Business, People, Governance, Platform, Security, Operations |
| e3d62fd0 | legacy | not retired | a | Business, People, Governance, Platform, Security, and Operations |
| 130a256a | legacy | not retired | a | Business, People, Governance, Platform, Security, and Operations |
| add0d64d | legacy | not retired | a | Business, People, Governance, Platform, Security, and Operations |
| d5bd2d4d | legacy | not retired | a | Business, People, Governance, Platform, Security, and Operations |

## A2. Near-duplicate bank questions

No embedding column is present in the generated_items SELECT * response. No worker stem-embedding dedupe path exists in this checkout. The audit uses the worker's actual `services/worker/app/embed.py:22` embed function with search_document for both stems and step text. All vectors are generated under one provider/model; no content-chunk or skill vectors are substituted for question vectors. Cache is local only.

Embedding provider: openai; model: text-embedding-3-small. Cosine is computed on normalized vectors. Counts are cumulative unordered pairs within each approved skill, never cross-skill pairs. High cosine is a review flag, not proof that two questions test identical knowledge.

| Course | Approved skill | Items | Pairs | >= .95 | >= .90 | >= .85 | >= .80 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ae4e7680 | 3b4046cf Compare and contrast traditional IT infrastructure with cloud computing models | 20 | 190 | 0 | 0 | 2 | 4 |
| ae4e7680 | 3ef47b2f Describe the six benefits of cloud computing and the six perspectives of the AWS Cloud Adoption Framework (AWS CAF) | 20 | 190 | 0 | 0 | 1 | 9 |
| ae4e7680 | 52828069 Explain AWS scalability, elasticity, and high availability principles | 20 | 190 | 0 | 0 | 0 | 0 |
| ae4e7680 | 7e3656fb Select appropriate AWS compute, storage, and database services for a given workload requirement | 20 | 190 | 0 | 1 | 3 | 6 |
| ae4e7680 | 910b1f7d Compare managed AWS services against self-managed alternatives based on operational and cost trade-offs | 12 | 66 | 0 | 0 | 0 | 2 |
| ae4e7680 | d678c6ee Identify core AWS service categories and their primary use cases | 20 | 190 | 0 | 0 | 1 | 7 |
| ae4e7680 | df7207ee Identify the purpose and primary use cases of core AWS compute, storage, and database services | 21 | 210 | 0 | 0 | 1 | 4 |
| ae4e7680 | e269882f Define cloud computing and its essential characteristics | 12 | 66 | 0 | 1 | 2 | 2 |
| ae4e7680 | eed94898 Identify appropriate AWS service categories (compute, storage, database, networking) for given business requirements | 48 | 1128 | 1 | 2 | 6 | 13 |

| Course totals | Items | Pairs | >= .95 | >= .90 | >= .85 | >= .80 |
| --- | --- | --- | --- | --- | --- | --- |
| 4f14665c | 0 | 0 | 0 | 0 | 0 | 0 |
| 5a34472f | 0 | 0 | 0 | 0 | 0 | 0 |
| 6b83b489 | 0 | 0 | 0 | 0 | 0 | 0 |
| ade5c095 | 0 | 0 | 0 | 0 | 0 | 0 |
| ae4e7680 | 193 | 2420 | 1 | 4 | 16 | 47 |

### 15 highest-similarity pairs

| Cosine | Skill | Item A | Prompt A (100) | Item B | Prompt B (100) |
| --- | --- | --- | --- | --- | --- |
| 0.972693 | eed94898 | 1eab6526 | A company needs a fully managed, petabyte-scale data warehouse to run complex analytical queries on  | 6d37ec42 | A company needs a petabyte-scale data warehouse to run complex analytical queries on large datasets. |
| 0.928788 | eed94898 | 8c5ca97f | A company needs to create a logically isolated section of the AWS Cloud where they can launch resour | 8c616fa8 | A company needs to create a logically isolated virtual network in the AWS Cloud where it can launch  |
| 0.920524 | e269882f | 624a58fa | Which set lists the three cloud deployment models? | 76430cea | Which set lists the three cloud service models? |
| 0.902748 | 7e3656fb | 57bdb7c8 | A media company needs to store and retrieve large numbers of video files and images with high durabi | 5b555602 | A company needs to store and retrieve large media files and serve them directly to users over the in |
| 0.887448 | eed94898 | 2b7aaeb7 | A research institution needs to archive large datasets for long-term retention at the lowest possibl | bffe8f70 | A company needs to archive data for long-term retention at low cost, with retrieval times ranging fr |
| 0.882450 | df7207ee | 30b8c3d9 | AWS Lambda is an example of which type of AWS service? | c812daaa | Amazon EC2 is an example of which type of AWS service? |
| 0.879702 | 7e3656fb | 1514fe48 | A media company needs to store and serve large video files to users over the internet, and it needs  | 5b555602 | A company needs to store and retrieve large media files and serve them directly to users over the in |
| 0.879218 | eed94898 | 145dd981 | A company wants to distribute static and dynamic web content to users worldwide with low latency by  | d13fa2d6 | A global media company wants to deliver videos and images to users with low latency by caching conte |
| 0.879196 | 3b4046cf | 71c9df5b | A company is planning its cloud adoption and needs to ensure that its employees are trained and that | fbf04161 | A company is adopting AWS and wants to ensure that its cloud environment is built on a well-architec |
| 0.877703 | eed94898 | 5f324ea7 | A company needs to store and retrieve any amount of data, such as backups and media files, with high | db4bc5cf | A media company needs to store and serve large video files to users around the world. The files must |
| 0.874700 | eed94898 | d73135a0 | A company needs a managed relational database service that automates patching, backups, and scaling. | f03b0021 | An online store needs a managed relational database to store customer orders and product information |
| 0.872194 | d678c6ee | 9dff6cd3 | Amazon CloudFront is grouped under which AWS service category? | fef7f841 | Amazon ECS is grouped under which AWS service category? |
| 0.867341 | 3ef47b2f | 0ff96a54 | Which of the following is NOT one of the six benefits of cloud computing? | 22b4c2dd | Which of the following is one of the six advantages of cloud computing? |
| 0.863596 | 3b4046cf | ad4c1a4c | A development team needs a cloud service model that provides a platform for developing and running a | ea2ffe0d | A development team needs maximum control over the operating system, networking, and storage configur |
| 0.862934 | 7e3656fb | 14e9ffc0 | An application requires a fully managed NoSQL database that can handle millions of requests per seco | e1a67fc8 | A company needs a NoSQL database service that can handle massive scale and provides low-latency acce |

### 10 calibration pairs: 0.80 <= cosine <= 0.88

| Cosine | Skill | Item A | Prompt A (100) | Item B | Prompt B (100) |
| --- | --- | --- | --- | --- | --- |
| 0.879702 | 7e3656fb | 1514fe48 | A media company needs to store and serve large video files to users over the internet, and it needs  | 5b555602 | A company needs to store and retrieve large media files and serve them directly to users over the in |
| 0.879218 | eed94898 | 145dd981 | A company wants to distribute static and dynamic web content to users worldwide with low latency by  | d13fa2d6 | A global media company wants to deliver videos and images to users with low latency by caching conte |
| 0.879196 | 3b4046cf | 71c9df5b | A company is planning its cloud adoption and needs to ensure that its employees are trained and that | fbf04161 | A company is adopting AWS and wants to ensure that its cloud environment is built on a well-architec |
| 0.877703 | eed94898 | 5f324ea7 | A company needs to store and retrieve any amount of data, such as backups and media files, with high | db4bc5cf | A media company needs to store and serve large video files to users around the world. The files must |
| 0.874700 | eed94898 | d73135a0 | A company needs a managed relational database service that automates patching, backups, and scaling. | f03b0021 | An online store needs a managed relational database to store customer orders and product information |
| 0.872194 | d678c6ee | 9dff6cd3 | Amazon CloudFront is grouped under which AWS service category? | fef7f841 | Amazon ECS is grouped under which AWS service category? |
| 0.867341 | 3ef47b2f | 0ff96a54 | Which of the following is NOT one of the six benefits of cloud computing? | 22b4c2dd | Which of the following is one of the six advantages of cloud computing? |
| 0.863596 | 3b4046cf | ad4c1a4c | A development team needs a cloud service model that provides a platform for developing and running a | ea2ffe0d | A development team needs maximum control over the operating system, networking, and storage configur |
| 0.862934 | 7e3656fb | 14e9ffc0 | An application requires a fully managed NoSQL database that can handle millions of requests per seco | e1a67fc8 | A company needs a NoSQL database service that can handle massive scale and provides low-latency acce |
| 0.855524 | e269882f | dd564b8a | In the cloud computing model, what should infrastructure no longer be thought of as? | de73c19c | In the cloud computing model, how should infrastructure be viewed? |

Current dedupe: normalized SHA-256 stem hash (`bank_build.py:89–91`), unique live bank index on (course_id, skill_id, stem_hash) (`packages/db/migrations/0021_question_bank.sql:22–24`); exact choice-set reuse rejection (`bank_build.py:260–263`); token-set Jaccard **> 0.8**, not cosine, against the latest 30 live stems and earlier accepted batch items (`bank_build.py:94–97`, `:275–280`, `:335–338`, `:491–508`). Rephrasing and synonyms can pass this lexical filter. No semantic dedupe occurs when selecting a test set (`services/api/app/bank/serving.py:40–68`, `:85–104`).

## A3. Assigned lesson checks

Scope: every stored guided lesson in every bank_serving=true course, including lessons whose skill is no longer approved. Read stored check ids without assigning missing ones. Off-topic heuristic: check prompt vs title + summary + detail_points < 0.45. There is no stored step title, so summary is used. Missing checks/text are N/A, not silently counted as on-topic. Check choices/explanations are not embedded. Step numbers and duplicate pairs below use the stored zero-based position: position 0 is the first step shown to a student.

Lessons audited: **9**; lessons with duplicate checks: **6**; steps flagged off-topic: **2**; total steps: **41**. Missing check rows: 0. Stored checks currently hidden by retired/unapproved filtering: 10. Lessons with a duplicate pair where both checks are currently displayable: 5.

| Lesson | Title | Skill status | Steps | Duplicate pairs | Off-topic steps |
| --- | --- | --- | --- | --- | --- |
| 066707a8 | Identify the purpose and primary use cases of core AWS compute, storage, and database services | approved | 5 | 0 | 0 |
| 3cebf7fa | Define cloud computing and its essential characteristics | approved | 5 | 1 | 0 |
| 47e8d3ac | Describe the six benefits of cloud computing and the six perspectives of the AWS Cloud Adoption Framework (AWS CAF) | approved | 5 | 3 | 2 |
| 4c2762bd | Compare managed AWS services against self-managed alternatives based on operational and cost trade-offs | approved | 5 | 1 | 0 |
| 512ce3a5 | Configure auto scaling policies and CloudWatch monitoring to maintain reliability and cost efficiency | approved | 1 | 0 | 0 |
| 6c534f49 | Evaluate personal readiness for AWS Cloud Practitioner certification | rejected | 5 | 0 | 0 |
| 78523e5e | Distinguish between IaaS, PaaS, and SaaS service models and cloud-based, hybrid, and on-premises deployment models | approved | 5 | 2 | 0 |
| 8c604e56 | Compare and contrast traditional IT infrastructure with cloud computing models | approved | 5 | 3 | 0 |
| a47785b5 | Compile course deliverables for AWS course badge submission | rejected | 5 | 3 | 0 |

### Every lesson and step

#### 066707a8: Identify the purpose and primary use cases of core AWS compute, storage, and database services

| Step | Summary (60) | Bloom | Check | Check prompt (80) | Cosine to step | Flags |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | This step introduces AWS Compute services, which provide the | remember | 17796a14 | Which AWS service provides processing power for running applications? | 0.738713 |  |
| 1 | This step focuses on recognizing that AWS Storage services a | remember | d20c0202 | What is the primary purpose of Amazon S3? | 0.559679 |  |
| 2 | This step focuses on recalling that Amazon RDS and Amazon Dy | remember | 825c0a5c | Which AWS service is designed for running code without managing infrastructure? | 0.537349 |  |
| 3 | This step introduces the idea that AWS services are designed | remember | 874784e5 | Which AWS service is a managed relational database service? | 0.508575 |  |
| 4 | Match core AWS services (EC2, Lambda, S3, EBS, RDS, DynamoDB | remember | 35072bbf | Which AWS service is a NoSQL database service? | 0.580561 |  |

Duplicate step pairs: none

#### 3cebf7fa: Define cloud computing and its essential characteristics

| Step | Summary (60) | Bloom | Check | Check prompt (80) | Cosine to step | Flags |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | This step asks you to recall from memory the core definition | remember | 010bd591 | What is cloud computing? | 0.668193 |  |
| 1 | This step focuses on recalling the essential characteristics | remember | de73c19c | In the cloud computing model, how should infrastructure be viewed? | 0.631640 |  |
| 2 | This step focuses on recognizing the three cloud service mod | understand | c56909db | Which pricing approach is a defining characteristic of cloud computing? | 0.523005 |  |
| 3 | This step focuses on identifying and differentiating the thr | understand | 76430cea | Which set lists the three cloud service models? | 0.591837 | duplicate |
| 4 | This step focuses on distinguishing cloud computing from tra | apply | 624a58fa | Which set lists the three cloud deployment models? | 0.485066 | duplicate |

Duplicate step pairs: 3–4: 0.920524

#### 47e8d3ac: Describe the six benefits of cloud computing and the six perspectives of the AWS Cloud Adoption Framework (AWS CAF)

| Step | Summary (60) | Bloom | Check | Check prompt (80) | Cosine to step | Flags |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | This step focuses on recalling the six key advantages of clo | remember | dfec6615 | How many perspectives make up the AWS Cloud Adoption Framework (AWS CAF), and wh | 0.411374 | off-topic |
| 1 | List and recall the six core perspectives of the AWS Cloud A | remember | a6ef6252 | Which set correctly identifies the six perspectives of the AWS Cloud Adoption Fr | 0.748843 | duplicate |
| 2 | This step explains how each of the six cloud computing benef | understand | 9973edc4 | Which of the following correctly lists the six perspectives of the AWS Cloud Ado | 0.517961 | duplicate |
| 3 | This step explains how the six AWS CAF perspectives group bu | understand | 880b0118 | Which of the following correctly lists the six perspectives of the AWS Cloud Ado | 0.799513 | duplicate |
| 4 | Each of the six AWS CAF perspectives (Business, People, Gove | apply | 4920ca0c | Which of the following lists the six benefits of cloud computing that are common | 0.311725 | off-topic |

Duplicate step pairs: 1–2: 0.905905; 1–3: 0.905905; 2–3: 1.000000

#### 4c2762bd: Compare managed AWS services against self-managed alternatives based on operational and cost trade-offs

| Step | Summary (60) | Bloom | Check | Check prompt (80) | Cosine to step | Flags |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | This step introduces the skill of comparing managed AWS serv | remember | 06393940 | When deciding between a managed AWS service and a self-managed alternative, whic | 0.793803 |  |
| 1 | This step introduces the two main categories of trade-offs t | understand | 537142b9 | According to the excerpt, what is the primary basis for comparing managed AWS se | 0.728017 |  |
| 2 | This step teaches you to take a real AWS scenario and line u | apply | b24beffe | Which statement best matches: Compare managed AWS services against self-managed  | 0.789494 | duplicate |
| 3 | This step teaches you to evaluate managed versus self-manage | analyze | bda9178c | Which statement best matches: Compare managed AWS services against self-managed  | 0.782641 | duplicate |
| 4 | This step asks you to weigh the evidence from earlier compar | evaluate | cca06205 | Based on the operational and cost trade-offs discussed in the excerpt, which eva | 0.737066 |  |

Duplicate step pairs: 2–3: 1.000000

#### 512ce3a5: Configure auto scaling policies and CloudWatch monitoring to maintain reliability and cost efficiency

| Step | Summary (60) | Bloom | Check | Check prompt (80) | Cosine to step | Flags |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | This step explains how AWS Auto Scaling and CloudWatch monit | apply | efd53ac5 | A company wants to ensure its application automatically adjusts resource capacit | 0.705554 |  |

Duplicate step pairs: none

#### 6c534f49: Evaluate personal readiness for AWS Cloud Practitioner certification

| Step | Summary (60) | Bloom | Check | Check prompt (80) | Cosine to step | Flags |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | This step focuses on recalling that the AWS Certified Cloud  | remember | dfd37eb5 | A learner has completed the AWS Academy Cloud Foundations course and earned the  | 0.750084 | hidden |
| 1 | This step clarifies what the AWS Academy Cloud Foundations c | understand | 568d2aaf | A person with no prior IT or cloud experience wants to switch to a cloud career. | 0.550386 | hidden |
| 2 | This step focuses on recognizing that the AWS Academy Cloud  | remember | cccb7f49 | What does earning the AWS Cloud Practitioner course badge indicate about a learn | 0.623727 | hidden |
| 3 | This step guides you to compare your own IT or cloud experie | analyze | 4d6d097f | A learner wants to validate their foundational, high-level understanding of AWS  | 0.679398 | hidden |
| 4 | This step guides you through assessing whether you are ready | evaluate | 72abaed0 | A learner wants to show employers they have foundational AWS cloud knowledge but | 0.636180 | hidden |

Duplicate step pairs: none

#### 78523e5e: Distinguish between IaaS, PaaS, and SaaS service models and cloud-based, hybrid, and on-premises deployment models

| Step | Summary (60) | Bloom | Check | Check prompt (80) | Cosine to step | Flags |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | This step introduces the three cloud service models—IaaS, Pa | remember | 2dba9942 | A team wants to run its own custom application code but does not want to manage  | 0.496232 | duplicate |
| 1 | Explain how control over IT resources decreases from IaaS to | understand | c247ec59 | A company wants to move its operations to the cloud but must keep certain sensit | 0.522846 |  |
| 2 | Identify cloud-based, hybrid, and on-premises (private cloud | remember | 7d6a0b98 | A company wants to run its own custom application code but avoid managing the un | 0.509014 | duplicate |
| 3 | This step explains the difference among cloud-based, hybrid, | understand | 4a5fc957 | A company wants to give its developers a managed environment where they can buil | 0.577735 | duplicate |
| 4 | This step teaches you to match IT scenarios to the right clo | apply | d6de260c | A company wants to give its software development team a managed environment for  | 0.637515 | duplicate |

Duplicate step pairs: 0–2: 0.961073; 3–4: 0.944838

#### 8c604e56: Compare and contrast traditional IT infrastructure with cloud computing models

| Step | Summary (60) | Bloom | Check | Check prompt (80) | Cosine to step | Flags |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | This step introduces traditional IT infrastructure, which re | remember | e0ae3d05 | Based on the concepts of traditional IT infrastructure and cloud computing model | 0.629016 |  |
| 1 | This step introduces cloud computing models by focusing on t | remember | 545935fd | Based on the excerpt's focus on comparing and contrasting traditional IT infrast | 0.658111 | duplicate |
| 2 | This step compares how traditional IT infrastructure and clo | understand | 7aade4ee | Based on the excerpt 'Compare and contrast traditional IT infrastructure with cl | 0.725972 | duplicate |
| 3 | This step teaches you how to systematically compare traditio | apply | 3f37b857 | Based on the excerpt, which of the following statements best compares and contra | 0.735563 | duplicate |
| 4 | This step examines the strengths and weaknesses of tradition | analyze | 5d179f06 | How do traditional IT infrastructure and cloud computing models fundamentally di | 0.690503 |  |

Duplicate step pairs: 1–2: 0.942281; 1–3: 0.904693; 2–3: 0.924635

#### a47785b5: Compile course deliverables for AWS course badge submission

| Step | Summary (60) | Bloom | Check | Check prompt (80) | Cosine to step | Flags |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | This step helps you recall the specific deliverables (artifa | remember | b73fd2f3 | Based on the course excerpt about compiling deliverables for AWS course badge su | 0.761945 | hidden, duplicate |
| 1 | This step focuses on understanding what each required artifa | understand | 8026a080 | A learner is preparing to compile their course deliverables for an AWS course ba | 0.695221 | hidden |
| 2 | This step guides you to gather and organize everything you p | apply | 0088e1fb | Based on the course excerpt, which of the following is a required deliverable fo | 0.714250 | hidden |
| 3 | This step focuses on reviewing each compiled course artifact | analyze | be688c19 | Based on the course excerpt 'Compile course deliverables for AWS course badge su | 0.764215 | hidden, duplicate |
| 4 | This step focuses on gathering and packaging all the work yo | create | 2b297f27 | Which of the following is the correct first step when compiling course deliverab | 0.770312 | hidden, duplicate |

Duplicate step pairs: 0–3: 0.932977; 0–4: 0.908009; 3–4: 0.952435

### Five worst lessons in full

Ranked by off-topic count descending, duplicate-pair count descending, minimum relevance ascending, then lesson id. These thresholds need human review; related topics can score high without matching the step's teaching objective.

#### 47e8d3ac: Describe the six benefits of cloud computing and the six perspectives of the AWS Cloud Adoption Framework (AWS CAF)

**Step 0 — remember**

This step focuses on recalling the six key advantages of cloud computing as outlined in the course excerpt, which describe how cloud computing improves cost efficiency, speed, scalability, and global reach compared to traditional IT infrastructure.
Cloud computing lets you trade large upfront capital expenses for variable costs based on actual usage.
Economies of scale from AWS's large infrastructure help reduce overall costs.
You no longer need to guess capacity requirements because resources can scale on demand, and deployments happen in minutes rather than weeks.
Cloud computing reduces data center management overhead and enables global deployment so you can reach users in multiple regions.
A common misconception is that cloud computing eliminates all costs — in reality, you still pay for the resources you consume; it shifts spending from capital expenditure to variable operational expenditure rather than removing cost entirely.
Cloud computing's six benefits collectively transform how organizations spend money, deploy quickly, scale flexibly, manage infrastructure, and reach users worldwide.

**Assigned check:** How many perspectives make up the AWS Cloud Adoption Framework (AWS CAF), and which of the following correctly lists them?

Check id: dfec6615; cosine: 0.411374; currently displayable: True.

**Step 1 — remember**

List and recall the six core perspectives of the AWS Cloud Adoption Framework: Business, People, Governance, Platform, Security, and Operations, along with their general purpose from the excerpt.

**Assigned check:** Which set correctly identifies the six perspectives of the AWS Cloud Adoption Framework (AWS CAF)?

Check id: a6ef6252; cosine: 0.748843; currently displayable: True.

**Step 2 — understand**

This step explains how each of the six cloud computing benefits maps to reducing cost, increasing agility, and enabling scalability for organizations moving to the cloud.
Replacing large upfront capital expenses with variable costs based on actual usage directly reduces cost, since you pay only for what you consume rather than investing in forecasted data center capacity.
Benefiting from AWS's large scale reduces cost by leveraging economies of scale that individual on-premises data centers cannot achieve.
Scaling resources on demand instead of guessing theoretical maximum peaks increases agility and enables scalability, eliminating long hardware procurement cycles and capacity over-provisioning.
Launching services in minutes instead of waiting weeks for hardware increases agility, while deploying applications globally enables scalability by reaching users across multiple regions, and spending less on data center management reduces cost.
Learners often assume all six benefits are primarily about cost savings, when in fact benefits like on-demand scaling, rapid deployment, and global reach primarily drive agility and scalability rather than just reducing cost.
The six cloud benefits collectively address three organizational goals — cost reduction, agility, and scalability — with each benefit contributing to one or more of these outcomes.

**Assigned check:** Which of the following correctly lists the six perspectives of the AWS Cloud Adoption Framework (AWS CAF)?

Check id: 9973edc4; cosine: 0.517961; currently displayable: True.

**Step 3 — understand**

This step explains how the six AWS CAF perspectives group business and technical capabilities to help organizations align IT strategy with business goals and minimize risk throughout the cloud adoption journey.
The AWS CAF organizes guidance into six perspectives: Business, People, Governance, Platform, Security, and Operations.
Each perspective consists of sets of business or technology capabilities assigned to key stakeholders such as business managers, CTOs, CISOs, and IT operations managers.
The perspectives cover both business capabilities (e.g., IT finance, organizational change management) and technical capabilities (e.g., compute provisioning, infrastructure security).
Together, the perspectives help organizations maximize the business value of IT investments and minimize business risks across the cloud adoption journey.
A common misconception is that the six CAF perspectives are only technical IT concerns, when in fact perspectives like Business and People focus on organizational and strategic capabilities that are equally critical to cloud success.
The six AWS CAF perspectives collectively ensure that both business and technical capabilities are addressed so IT strategy stays aligned with business goals during cloud adoption.

**Assigned check:** Which of the following correctly lists the six perspectives of the AWS Cloud Adoption Framework (AWS CAF)?

Check id: 880b0118; cosine: 0.799513; currently displayable: True.

**Step 4 — apply**

Each of the six AWS CAF perspectives (Business, People, Governance, Platform, Security, Operations) is the responsibility of specific stakeholder roles as defined in the AWS CAF framework.
The Business perspective is owned by business managers, finance managers, budget owners, and strategy stakeholders.
The People perspective is owned by human resources, staffing, and people managers.
The Governance perspective is owned by the CIO, program managers, enterprise architects, business analysts, and portfolio managers.
The Platform perspective is owned by the CTO, IT managers, and solutions architects; the Security perspective by the CISO, IT security managers, and IT security analysts; and the Operations perspective by IT operations managers and IT support managers.
A common misconception is that the CISO alone is responsible for the entire Security perspective, when in fact IT security managers and IT security analysts share responsibility for its capabilities such as identity management, infrastructure security, and incident response.
Each AWS CAF perspective has designated stakeholder roles responsible for its capabilities, ensuring that business, technical, and security responsibilities are clearly distributed across the organization.

**Assigned check:** Which of the following lists the six benefits of cloud computing that are commonly identified when moving away from traditional data centers?

Check id: 4920ca0c; cosine: 0.311725; currently displayable: True.

Duplicate pairs: 1–2: 0.905905; 1–3: 0.905905; 2–3: 1.000000

#### 8c604e56: Compare and contrast traditional IT infrastructure with cloud computing models

**Step 0 — remember**

This step introduces traditional IT infrastructure, which refers to computing resources that an organization owns and operates within its own physical facilities. The focus is on helping learners recall its core characteristics: on-premises servers, dedicated hardware, and fixed capacity planning, which together shape how traditional environments are built and managed.
On-premises servers are physical machines located and maintained inside the organization's own data center or server room.
Dedicated hardware means each system is assigned to specific workloads, rather than being shared flexibly across many applications.
Fixed capacity planning requires organizations to estimate resource needs in advance and provision hardware accordingly, often leading to underused or insufficient capacity.
Together, these traits make traditional IT infrastructure capital-intensive and slower to change compared to more flexible models.
A common misconception is that traditional IT infrastructure is always outdated or inefficient; in reality, it simply operates under different trade-offs, prioritizing direct control and ownership over flexibility and rapid scaling.
Traditional IT infrastructure is defined by on-premises, dedicated hardware and fixed capacity planning, giving organizations control but limiting flexibility.

**Assigned check:** Based on the concepts of traditional IT infrastructure and cloud computing models, which statement best analyzes a key trade-off between the two approaches?

Check id: e0ae3d05; cosine: 0.629016; currently displayable: True.

**Step 1 — remember**

This step introduces cloud computing models by focusing on their defining features: on-demand resources, scalability, virtualization, and service-based delivery. These characteristics distinguish cloud computing from traditional, fixed IT infrastructure.
On-demand resources let users provision computing power, storage, and services whenever they need them, without long procurement cycles.
Scalability allows capacity to grow or shrink based on demand, unlike traditional infrastructure that is sized for peak loads.
Virtualization abstracts physical hardware into flexible, software-defined resources that can be allocated dynamically.
Service-based delivery means computing capabilities are consumed as managed services over the network, rather than owned and operated on-premise.
A common misconception is that cloud computing simply means storing files on someone else's server; in reality, it is a broader model built on virtualization, elasticity, and on-demand service delivery.
Cloud computing is defined by on-demand, scalable, virtualized resources delivered as services over a network.

**Assigned check:** Based on the excerpt's focus on comparing and contrasting traditional IT infrastructure with cloud computing models, which of the following best analyzes a key distinction between the two?

Check id: 545935fd; cosine: 0.658111; currently displayable: True.

**Step 2 — understand**

This step compares how traditional IT infrastructure and cloud computing differ in provisioning, maintenance, scalability, and cost structure, contrasting upfront capital expenditure with ongoing operational expenditure.
Traditional IT requires manual provisioning: hardware must be purchased, installed, and configured before use, often taking weeks or months.
Cloud computing enables on-demand provisioning through self-service portals or APIs, so resources are available in minutes.
Maintenance is the organization's responsibility on-premises (servers, cooling, patches, upgrades), whereas the cloud provider handles underlying infrastructure maintenance.
Scalability differs: traditional infrastructure scales by buying and installing more hardware (slow, lumpy), while cloud scales elastically up or down based on demand.
A common misconception is that cloud computing is always cheaper than traditional IT; in reality, costs depend on usage patterns, and poorly managed cloud resources can exceed on-premises costs.
Traditional IT trades flexibility for control via upfront CapEx, while cloud trades control for agility via ongoing OpEx.

**Assigned check:** Based on the excerpt 'Compare and contrast traditional IT infrastructure with cloud computing models', which of the following best analyzes the key difference between these two approaches?

Check id: 7aade4ee; cosine: 0.725972; currently displayable: True.

**Step 3 — apply**

This step teaches you how to systematically compare traditional IT infrastructure and cloud computing using a structured framework, so the comparison is organized rather than just a list of differences.
The framework breaks the comparison into set dimensions: deployment time, flexibility, control, security responsibility, and cost.
For each dimension, you decide how each model scores, e.g., traditional IT is slow to deploy and capital-heavy, while cloud is fast to deploy and often pay-as-you-go.
Using the same dimensions for both models forces a like-for-like comparison and highlights trade-offs instead of just pros and cons.
The output is typically a side-by-side table or aligned bullet lists that makes the contrasts easy to scan and discuss.
A common misconception is that cloud is always better on every dimension; the framework actually shows trade-offs, for example traditional IT can offer more direct control while cloud can offer more flexibility.
Compare the two models dimension by dimension (deployment time, flexibility, control, security responsibility, cost) so the trade-offs, not just the differences, become clear.

**Assigned check:** Based on the excerpt, which of the following statements best compares and contrasts traditional IT infrastructure with cloud computing models?

Check id: 3f37b857; cosine: 0.735563; currently displayable: True.

**Step 4 — analyze**

This step examines the strengths and weaknesses of traditional IT infrastructure versus cloud computing to determine which approach best fits a given situation.
Traditional IT offers maximum control and customization, making it well-suited for highly regulated workloads, predictable steady-state demand, and organizations with mature in-house IT capabilities.
Cloud computing excels in scalability, speed of provisioning, and cost flexibility, making it ideal for variable workloads, rapid growth, or projects requiring quick deployment without large upfront capital.
Key trade-off factors include workload type (steady vs. variable), compliance and data residency requirements, and the organization's IT maturity and ability to manage infrastructure.
No single model is universally superior; the right choice depends on aligning technical characteristics with business priorities such as cost predictability, agility, control, and risk tolerance.
Many learners assume cloud computing is always cheaper or better than traditional IT, when in reality the best fit depends on workload characteristics, compliance needs, and organizational maturity.
Choose traditional IT or cloud based on matching workload patterns, compliance demands, and organizational maturity rather than assuming one model is inherently superior.

**Assigned check:** How do traditional IT infrastructure and cloud computing models fundamentally differ in their approach to resource provisioning and management?

Check id: 5d179f06; cosine: 0.690503; currently displayable: True.

Duplicate pairs: 1–2: 0.942281; 1–3: 0.904693; 2–3: 0.924635

#### a47785b5: Compile course deliverables for AWS course badge submission

**Step 0 — remember**

This step helps you recall the specific deliverables (artifacts) and submission criteria required for the AWS course badge, so you can gather and prepare the correct items before assembling your submission package.
Badge artifacts are the individual pieces of work or evidence you must submit to earn the AWS course badge.
Submission criteria are the rules or standards each artifact must meet to be accepted (for example, required format, completed sections, or correct filenames).
Before you start compiling, list every artifact and its matching criteria so nothing is missed at submission time.
The provided course excerpt does not specify the exact artifacts or criteria, so you will need to confirm the full list from your course materials or instructor.
Assuming every AWS badge requires the same set of deliverables, rather than checking the specific artifact list for the particular course badge you are pursuing.
Always confirm the exact required artifacts and their submission criteria for your specific AWS course badge before you start compiling your evidence.

**Assigned check:** Based on the course excerpt about compiling deliverables for AWS course badge submission, which of the following is the most appropriate first step a learner should take when preparing their submission package?

Check id: b73fd2f3; cosine: 0.761945; currently displayable: False.

**Step 1 — understand**

This step focuses on understanding what each required artifact for the AWS course badge submission must accomplish, how it should be formatted, and what kind of evidence it must contain to demonstrate competency.
Identify the purpose of each artifact: know what competency or skill each deliverable is meant to demonstrate to badge reviewers.
Follow the required formatting: adhere to specified file types, naming conventions, length limits, and structural templates provided in the submission guidelines.
Include concrete evidence: incorporate screenshots, code snippets, diagrams, or outputs that clearly show hands-on completion of AWS tasks.
Review expectations before compiling: distinguish between optional supporting materials and mandatory items to avoid missing required components.
Assuming that simply completing the AWS labs or coursework is enough, without packaging the work into the specifically formatted artifacts reviewers expect.
Every artifact must be intentionally shaped—purpose, format, and evidence—to clearly prove the required competency to badge reviewers.

**Assigned check:** A learner is preparing to compile their course deliverables for an AWS course badge submission. Which of the following is the correct sequence of items they should assemble?

Check id: 8026a080; cosine: 0.695221; currently displayable: False.

**Step 2 — apply**

This step guides you to gather and organize everything you produced during the AWS course into one tidy package for badge submission.
Identify all required deliverables: completed labs, projects, quizzes, and reflection prompts listed in the course requirements.
Place each item into a single, clearly named folder structure (e.g., /Labs, /Projects, /Reflections) so reviewers can locate them quickly.
Verify file formats are accepted (PDF, ZIP, or links) and rename files consistently, including your name and the deliverable type.
Cross-check the submission checklist against your folder to confirm nothing is missing before uploading or sending.
Assuming a badge only needs a certificate — most badges also require evidence of the actual coursework and reflections, not just proof of attendance.
A well-organized, checklist-verified submission package makes your badge review faster and far more likely to be approved.

**Assigned check:** Based on the course excerpt, which of the following is a required deliverable for AWS course badge submission?

Check id: 0088e1fb; cosine: 0.714250; currently displayable: False.

**Step 3 — analyze**

This step focuses on reviewing each compiled course artifact against the AWS course badge submission checklist to confirm that every required deliverable is present, properly formatted, and supported by the expected evidence.
Cross-check each artifact (e.g., project files, screenshots, documentation) against the rubric items listed in the submission checklist.
Flag any deliverable that is missing, incomplete, or lacks the required evidence such as diagrams, source code, or signed-off documentation.
Record gaps and required corrections in a simple tracking note so they can be addressed before final submission.
Assuming that simply collecting files in a folder is enough — the AWS badge review requires matching artifacts to specific rubric criteria, not just having related materials.
Every rubric line item must map to a specific artifact with clear evidence before the AWS course badge can be submitted.

**Assigned check:** Based on the course excerpt 'Compile course deliverables for AWS course badge submission', which of the following is the most appropriate first step when compiling deliverables for an AWS course badge submission?

Check id: be688c19; cosine: 0.764215; currently displayable: False.

**Step 4 — create**

This step focuses on gathering and packaging all the work you produced throughout the course into a single, organized set of files that meets AWS's requirements for earning a course badge.
Gather every required artifact, such as completed labs, project files, screenshots, or assessments, into one folder.
Arrange the artifacts in the exact order or naming convention the AWS submission guidelines specify.
Double-check that the package contains nothing extra and nothing missing before you send it for upload.
Assuming you can submit your work in whatever format feels easiest to you, rather than following the exact file structure and naming rules AWS expects.
A successful badge submission depends on packaging your deliverables precisely as AWS requires, not just on having completed the course work.

**Assigned check:** Which of the following is the correct first step when compiling course deliverables for AWS course badge submission?

Check id: 2b297f27; cosine: 0.770312; currently displayable: False.

Duplicate pairs: 0–3: 0.932977; 0–4: 0.908009; 3–4: 0.952435

#### 78523e5e: Distinguish between IaaS, PaaS, and SaaS service models and cloud-based, hybrid, and on-premises deployment models

**Step 0 — remember**

This step introduces the three cloud service models—IaaS, PaaS, and SaaS—and explains how they differ in the level of control users have over IT resources.
IaaS (Infrastructure as a Service) gives users the most control over IT resources.
PaaS (Platform as a Service) provides a platform for developing and running applications.
SaaS (Software as a Service) provides ready-to-use software with less need for technical management.
The models form a spectrum from more control (IaaS) to less control (SaaS) over IT resources.
A common misconception is that all three service models give users the same level of control over IT resources, when in reality IaaS offers the most control and SaaS the least.
The three cloud service models—IaaS, PaaS, and SaaS—exist on a spectrum from most to least user control over IT resources.

**Assigned check:** A team wants to run its own custom application code but does not want to manage the underlying operating system, servers, or runtime environment. Which cloud service model best matches this requirement?

Check id: 2dba9942; cosine: 0.496232; currently displayable: True.

**Step 1 — understand**

Explain how control over IT resources decreases from IaaS to PaaS to SaaS, and match each model to its appropriate use case based on the level of technical management required.

**Assigned check:** A company wants to move its operations to the cloud but must keep certain sensitive systems running in its own data center while connecting them to cloud resources. Which cloud deployment model does this describe?

Check id: c247ec59; cosine: 0.522846; currently displayable: True.

**Step 2 — remember**

Identify cloud-based, hybrid, and on-premises (private cloud) as the three deployment models, defined by where resources are hosted.

**Assigned check:** A company wants to run its own custom application code but avoid managing the underlying servers, operating systems, and runtime environment. Which cloud service model best matches this need?

Check id: 7d6a0b98; cosine: 0.509014; currently displayable: True.

**Step 3 — understand**

This step explains the difference among cloud-based, hybrid, and on-premises deployment models by examining where IT resources are located and who manages them, using the traditional IT vs. cloud comparison as context.
Traditional IT (on-premises) requires businesses to buy and maintain physical servers and data centers, which is expensive and requires careful planning.
Cloud computing provides flexible IT resources as services over the internet, eliminating the need to manage physical data centers and reducing maintenance effort.
There are three cloud deployment models: cloud, hybrid, and on-premises (private cloud), and the choice depends on where resources are hosted and managed.
Almost anything implementable with traditional IT can also be implemented as an AWS cloud service, since both share similar functions like networking, compute, storage, and security.
A common misconception is that on-premises infrastructure and cloud infrastructure are fundamentally different technologies, when in fact they serve the same purposes (firewalls, compute, storage, networking) and differ primarily in where resources are located and who manages them.
Deployment models differ based on where IT resources are physically located and who is responsible for managing them — on-premises means you host and manage it yourself, cloud means the provider hosts and manages it, and hybrid combines both.

**Assigned check:** A company wants to give its developers a managed environment where they can build, deploy, and run their own applications without having to manage the underlying servers or operating systems, but they still want more control than a finished software product would provide. Which cloud service model best fits this need?

Check id: 4a5fc957; cosine: 0.577735; currently displayable: True.

**Step 4 — apply**

This step teaches you to match IT scenarios to the right cloud service model (IaaS, PaaS, SaaS) and deployment model (cloud, hybrid, on-premises) based on needs like control level, ready-to-use software, or mixed hosting environments.
IaaS gives users the most control over IT resources, PaaS provides a platform for developing and running applications, and SaaS provides ready-to-use software with less need for technical management.
Deployment models describe where resources are hosted: cloud-based, hybrid, or on-premises (private cloud).
Service models and deployment models address different questions — service models define what you use, while deployment models define where you host it.
The choice depends on your scenario: maximum control points to IaaS, ready-to-use software points to SaaS, and mixed hosting points to a hybrid deployment.
A common mistake is confusing service models with deployment models — for example, thinking SaaS is a deployment option or that on-premises is a service model, when they describe entirely different aspects of cloud computing.
Service models (IaaS/PaaS/SaaS) determine how much control and management you have, while deployment models (cloud/hybrid/on-premises) determine where your resources live — always evaluate both when matching a scenario to the right cloud approach.

**Assigned check:** A company wants to give its software development team a managed environment for building and deploying applications without the team having to configure or maintain the underlying servers and operating systems themselves. They still want to write and run their own code. Which cloud service model best fits this requirement?

Check id: d6de260c; cosine: 0.637515; currently displayable: True.

Duplicate pairs: 0–2: 0.961073; 3–4: 0.944838

#### 3cebf7fa: Define cloud computing and its essential characteristics

**Step 0 — remember**

This step asks you to recall from memory the core definition of cloud computing: it is the on-demand delivery of compute power, database, storage, applications, and other IT resources via the internet with pay-as-you-go pricing.
Cloud computing delivers IT resources such as compute, storage, databases, and applications over the internet.
Resources are provided on-demand, meaning they are available when you need them.
You pay only for the amount of resources you consume (pay-as-you-go pricing).
Cloud computing lets you think of infrastructure as software rather than physical hardware.
A common misconception is that cloud computing means you are simply renting someone else's physical servers — in reality, the key shift is that cloud computing lets you treat your infrastructure as software, eliminating the need to manage physical hardware.
Cloud computing is the on-demand delivery of IT resources via the internet with pay-as-you-go pricing.

**Assigned check:** What is cloud computing?

Check id: 010bd591; cosine: 0.668193; currently displayable: True.

**Step 1 — remember**

This step focuses on recalling the essential characteristics of cloud computing as defined in the course excerpt: on-demand delivery of IT resources via the internet, pay-as-you-go pricing, flexibility, scalability, and the elimination of heavy-lifting tasks tied to physical hardware management.
Cloud computing is the on-demand delivery of compute power, storage, databases, and applications via the internet with pay-as-you-go pricing.
Cloud infrastructure is treated as software rather than hardware, making it flexible and easier to change than physical solutions.
Cloud computing eliminates undifferentiated heavy-lifting tasks such as provisioning capacity by guessing theoretical maximum peaks.
Resources can be launched in minutes and scaled based on demand, instead of waiting weeks for physical hardware procurement.
A common misconception is that cloud computing still requires purchasing and maintaining physical servers — in reality, the cloud model replaces physical infrastructure with software-based resources delivered over the internet.
Cloud computing transforms infrastructure from physical hardware into on-demand, software-based services accessed via the internet, eliminating capacity guessing and heavy-lifting tasks.

**Assigned check:** In the cloud computing model, how should infrastructure be viewed?

Check id: de73c19c; cosine: 0.631640; currently displayable: True.

**Step 2 — understand**

This step focuses on recognizing the three cloud service models—IaaS, PaaS, and SaaS—and understanding how they differ in the level of control users have over IT resources.
IaaS (Infrastructure as a Service) gives users the most control over IT resources.
PaaS (Platform as a Service) provides a platform for developing and running applications.
SaaS (Software as a Service) offers ready-to-use software with less need for technical management.
The three models form a spectrum from more control (IaaS) to less control (SaaS) over IT resources.
A common misconception is that choosing a service model changes what you can build—in reality, the model only determines how much management responsibility you take on, not what is possible to create.
The three cloud service models—IaaS, PaaS, and SaaS—differ primarily in the amount of control and technical management responsibility they require from the user.

**Assigned check:** Which pricing approach is a defining characteristic of cloud computing?

Check id: c56909db; cosine: 0.523005; currently displayable: True.

**Step 3 — understand**

This step focuses on identifying and differentiating the three cloud deployment models based on where IT resources are hosted: Cloud (public cloud), Hybrid, and On-premises (private cloud).
Cloud deployment means resources are hosted by the cloud provider and accessed over the internet, shared across multiple organizations.
On-premises (private cloud) deployment means resources are hosted within your own data center or infrastructure, giving you full control.
Hybrid deployment combines both cloud and on-premises resources, allowing workloads to move between them as needed.
A common misconception is that 'cloud' and 'public cloud' are completely different things — in this context, the cloud deployment model referred to as 'cloud' is the same as public cloud, where resources are owned and operated by a third-party provider.
The three deployment models differ by location and ownership of resources: cloud (provider-hosted), on-premises (your own data center), and hybrid (a mix of both).

**Assigned check:** Which set lists the three cloud service models?

Check id: 76430cea; cosine: 0.591837; currently displayable: True.

**Step 4 — apply**

This step focuses on distinguishing cloud computing from traditional IT by evaluating scenarios against key criteria such as on-demand delivery, internet access, pay-as-you-go pricing, and the shift from hardware to software.
Traditional IT relies on physical hardware that requires space, staff, physical security, and long procurement cycles.
Cloud computing delivers infrastructure as software, enabling flexible, quick changes and eliminating the need to guess capacity peaks.
Cloud resources are provided on-demand via the internet with pay-as-you-go pricing, turning upfront capital expenses into variable expenses.
A common misconception is that cloud computing is simply renting someone else's physical hardware, rather than fundamentally shifting infrastructure from hardware to flexible software.
Cloud computing replaces rigid, hardware-based traditional IT with flexible, on-demand software delivered via the internet.

**Assigned check:** Which set lists the three cloud deployment models?

Check id: 624a58fa; cosine: 0.485066; currently displayable: True.

Duplicate pairs: 3–4: 0.920524

Assembly evidence: `services/api/app/learn/lessons.py:385–411`: skill-wide bank pool, prefer lesson source-chunk intersection, then oldest first, zip unassigned steps to available items. It excludes repeated ids but does not compare step text, Bloom level, or semantic similarity. Assigned legacy checks remain assigned. Display filtering is at lines 414–424. Review full teaching text before treating a cosine flag as a confirmed duplicate or off-topic check; related vocabulary can obscure different teaching objectives. The audit deliberately never invokes this function because lines 408–411 can write.

### Interpretation of the manual smoke findings

- The CAF lesson `47e8d3ac` confirms four of five checks ask about CAF perspectives. Its first step (stored position 0) teaches cloud benefits but asks about CAF perspectives: cosine **0.411374**. Its final step teaches CAF stakeholder roles but asks about cloud benefits: **0.311725**. Both fall below 0.45.
- The middle benefits step (stored position 2) also asks about CAF perspectives but scores **0.517961**. This is a visible conceptual mismatch that the proposed threshold misses.
- Two CAF checks have identical prompts (items `9973edc4` and `880b0118`, cosine **1.000000**), although their distractors differ. Another CAF pair scores **0.905905**. All these checks are legacy items.
- The highest bank pair is `1eab6526` / `6d37ec42` at **0.972693**, two petabyte-scale data-warehouse questions. Conversely, the service-model/deployment-model pair `624a58fa` / `76430cea` scores **0.920524** while asking about distinct categories. Cosine requires human review before removal or reassignment.
- The specific IaaS/PaaS/SaaS test-set pair from the manual smoke is **NOT CONFIRMED**: no set id or item ids were supplied, and this audit did not inspect student test history. The complete bank-pair distribution and examples above establish the current redundancy exposure without guessing which set was observed.
- The reported “No answer label” symptom remains **NOT CONFIRMED**. Active bank keys are valid, and all 16 matching legacy CAF prompts resolve to a stored label. This audit establishes current database content and code behavior; it does not reconstruct the earlier browser response.

## A4. Thin lesson steps

Thin steps: **3**. Same bank-serving-course lesson scope as A3. Total teaching text is newline-joined title (if stored), summary, detail_points, misconception, and key_takeaway, stripped per field; check prompt is excluded. Empty detail_points is flagged regardless of text length.

| Lesson | Step | Teaching characters | Key points | Reason |
| --- | --- | --- | --- | --- |
| 47e8d3ac | 1 | 195 | 0 | empty key points |
| 78523e5e | 1 | 176 | 0 | empty key points |
| 78523e5e | 2 | 132 | 0 | empty key points |

## Embedding accounting and limits

Embedding function calls recorded for this local cache: **263**; calls in this invocation: **0**; cached unique text hits: 273. No stored generated-item vectors were available. Provider/model: openai/text-embedding-3-small. No chat/completion or live database writes. Identical text shares one local cached vector; the count is outbound function invocations, not number of item pairs. No student identifiers or names are read into the report. Only course, skill, lesson, and item ids are shown, shortened to eight characters.
