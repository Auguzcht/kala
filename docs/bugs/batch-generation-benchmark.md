# AWS101 batched MCQ generation benchmark

Run: `2026-10-05T19:24:33.116503+00:00`; course: `ae4e7680-f94b-4652-b3f6-b9c32f4420de`; model: `deepseek/deepseek-v4.1-flash:floor`.

This run used the production `_MCQ_SYSTEM`, `_BANNED_STEM_PHRASES`, and `_validated_mcq` imports. It made no database writes and does not include prompts or full chunk text.

## Retrieval and depth

Recommended `SIM_THRESHOLD`: **0.544381**, selected by maximum Youden J over same-skill versus different-skill labels in the top-20 results. This is an inclusion cutoff, not a semantic guarantee: current tags are noisy, and the top retrieved rows frequently carry a different `skill_id`.

| Skill | Tagged chunks | Similarity-union depth | Same-skill matches | Different-skill | Null skill |
|---|---:|---:|---:|---:|---:|
| Compare managed AWS services against self-managed alternatives based on operational and cost trade-offs | 1 | 2 | 1 | 19 | 0 |
| Configure auto scaling policies and CloudWatch monitoring to maintain reliability and cost efficiency | 3 | 2 | 3 | 17 | 0 |
| Design a cloud architecture in AWS that satisfies scalability, high availability, and fault tolerance requirements | 2 | 2 | 2 | 18 | 0 |
| Distinguish between IaaS, PaaS, and SaaS service models and cloud-based, hybrid, and on-premises deployment models | 2 | 2 | 2 | 17 | 1 |
| Compare and contrast traditional IT infrastructure with cloud computing models | 1 | 3 | 1 | 18 | 1 |
| Describe the six benefits of cloud computing and the six perspectives of the AWS Cloud Adoption Framework (AWS CAF) | 6 | 8 | 6 | 14 | 0 |
| Identify appropriate AWS service categories (compute, storage, database, networking) for given business requirements | 6 | 8 | 5 | 15 | 0 |
| Compile course deliverables for AWS course badge submission | 4 | 9 | 4 | 14 | 2 |
| Identify AWS certification pathways and credential requirements | 12 | 10 | 10 | 10 | 0 |
| Evaluate personal readiness for AWS Cloud Practitioner certification | 4 | 11 | 1 | 18 | 1 |

### Top-20 match_content_items results

Scores are listed without chunk text or student data; `same_skill`, `different_skill`, and `null_skill` are based on the current `skill_id` tag.

#### Compare and contrast traditional IT infrastructure with cloud computing models

| Rank | Similarity | Label | Included at threshold | Content item |
|---:|---:|---|---|---|
| 1 | 0.590779 | different_skill | yes | `c07c6f7e-97f0-4622-af88-60f9f48f1917` |
| 2 | 0.574678 | different_skill | yes | `60c97b8a-c2e5-4aa7-bf7c-f5755c6bcc1b` |
| 3 | 0.546931 | different_skill | yes | `3a384117-ff82-4819-b75d-fcf797900ca0` |
| 4 | 0.521082 | different_skill | no | `97fe17f2-7777-4202-9904-2e26011fa5fd` |
| 5 | 0.487702 | different_skill | no | `b003b09d-9caf-4abb-b054-e50250b70f40` |
| 6 | 0.476379 | different_skill | no | `272b5c6f-3e55-475b-8839-9670d894603c` |
| 7 | 0.467568 | same_skill | no | `64c9f7dd-b6ef-4d01-b399-e14a8ade4779` |
| 8 | 0.456730 | different_skill | no | `ff8f8a77-7eb7-430b-bdf4-204993445b93` |
| 9 | 0.443055 | different_skill | no | `db641338-a1eb-41b6-b573-561b6de1264c` |
| 10 | 0.424553 | different_skill | no | `d7ac67f8-5e11-43bb-a7a0-9a38971556b2` |
| 11 | 0.423201 | different_skill | no | `cd9946af-d6de-4b36-81f0-bd5f2b0ab8e4` |
| 12 | 0.399591 | different_skill | no | `3573aea0-282a-4385-aeb5-88a5991c0926` |
| 13 | 0.393613 | different_skill | no | `6fb2bfba-1539-4c6f-a3cb-be23e59c9313` |
| 14 | 0.392750 | null_skill | no | `56f2c01e-ffe7-41af-b3da-a32911e11898` |
| 15 | 0.391895 | different_skill | no | `c12c50b5-1228-492a-be48-63d478b6274c` |
| 16 | 0.381619 | different_skill | no | `daaa80b2-5aff-4a9f-994f-43928d844668` |
| 17 | 0.378422 | different_skill | no | `db684279-fe2a-4b2b-b99d-e670560bab21` |
| 18 | 0.363905 | different_skill | no | `14f69a3d-1954-48f7-ac9c-269293dd855e` |
| 19 | 0.360779 | different_skill | no | `dbdca507-7596-4f42-b34b-e71134ed4d81` |
| 20 | 0.359869 | different_skill | no | `78792d6d-05b3-4cf1-ab74-bfdc607d9eed` |

#### Distinguish between IaaS, PaaS, and SaaS service models and cloud-based, hybrid, and on-premises deployment models

| Rank | Similarity | Label | Included at threshold | Content item |
|---:|---:|---|---|---|
| 1 | 0.605336 | same_skill | yes | `60c97b8a-c2e5-4aa7-bf7c-f5755c6bcc1b` |
| 2 | 0.544236 | different_skill | no | `64c9f7dd-b6ef-4d01-b399-e14a8ade4779` |
| 3 | 0.526199 | different_skill | no | `3a384117-ff82-4819-b75d-fcf797900ca0` |
| 4 | 0.525897 | same_skill | no | `c07c6f7e-97f0-4622-af88-60f9f48f1917` |
| 5 | 0.501257 | different_skill | no | `272b5c6f-3e55-475b-8839-9670d894603c` |
| 6 | 0.487023 | different_skill | no | `97fe17f2-7777-4202-9904-2e26011fa5fd` |
| 7 | 0.466180 | different_skill | no | `ff8f8a77-7eb7-430b-bdf4-204993445b93` |
| 8 | 0.445550 | different_skill | no | `d7ac67f8-5e11-43bb-a7a0-9a38971556b2` |
| 9 | 0.432846 | different_skill | no | `b003b09d-9caf-4abb-b054-e50250b70f40` |
| 10 | 0.407652 | different_skill | no | `db641338-a1eb-41b6-b573-561b6de1264c` |
| 11 | 0.405781 | different_skill | no | `78792d6d-05b3-4cf1-ab74-bfdc607d9eed` |
| 12 | 0.396890 | different_skill | no | `c12c50b5-1228-492a-be48-63d478b6274c` |
| 13 | 0.392881 | different_skill | no | `daaa80b2-5aff-4a9f-994f-43928d844668` |
| 14 | 0.388649 | different_skill | no | `6fb2bfba-1539-4c6f-a3cb-be23e59c9313` |
| 15 | 0.386319 | different_skill | no | `f7771acf-459d-4b0a-9ad4-4cd3e37241d7` |
| 16 | 0.374880 | different_skill | no | `14f69a3d-1954-48f7-ac9c-269293dd855e` |
| 17 | 0.369529 | different_skill | no | `db684279-fe2a-4b2b-b99d-e670560bab21` |
| 18 | 0.369446 | null_skill | no | `56f2c01e-ffe7-41af-b3da-a32911e11898` |
| 19 | 0.362010 | different_skill | no | `b7d3ec4e-017a-4a23-9da5-def88254a5b6` |
| 20 | 0.358986 | different_skill | no | `dbdca507-7596-4f42-b34b-e71134ed4d81` |

#### Identify appropriate AWS service categories (compute, storage, database, networking) for given business requirements

| Rank | Similarity | Label | Included at threshold | Content item |
|---:|---:|---|---|---|
| 1 | 0.655944 | different_skill | yes | `272b5c6f-3e55-475b-8839-9670d894603c` |
| 2 | 0.610529 | same_skill | yes | `d7ac67f8-5e11-43bb-a7a0-9a38971556b2` |
| 3 | 0.605388 | same_skill | yes | `78792d6d-05b3-4cf1-ab74-bfdc607d9eed` |
| 4 | 0.591593 | same_skill | yes | `f7771acf-459d-4b0a-9ad4-4cd3e37241d7` |
| 5 | 0.590448 | same_skill | yes | `c12c50b5-1228-492a-be48-63d478b6274c` |
| 6 | 0.580009 | different_skill | yes | `ff8f8a77-7eb7-430b-bdf4-204993445b93` |
| 7 | 0.557494 | same_skill | yes | `b7d3ec4e-017a-4a23-9da5-def88254a5b6` |
| 8 | 0.553483 | different_skill | yes | `97fe17f2-7777-4202-9904-2e26011fa5fd` |
| 9 | 0.546072 | different_skill | yes | `14f69a3d-1954-48f7-ac9c-269293dd855e` |
| 10 | 0.539024 | different_skill | no | `6fb2bfba-1539-4c6f-a3cb-be23e59c9313` |
| 11 | 0.534269 | different_skill | no | `64c9f7dd-b6ef-4d01-b399-e14a8ade4779` |
| 12 | 0.533968 | different_skill | no | `3a384117-ff82-4819-b75d-fcf797900ca0` |
| 13 | 0.530742 | different_skill | no | `b003b09d-9caf-4abb-b054-e50250b70f40` |
| 14 | 0.496296 | different_skill | no | `daaa80b2-5aff-4a9f-994f-43928d844668` |
| 15 | 0.492335 | different_skill | no | `43ba25e7-3dba-475a-8c19-6836fdd621b2` |
| 16 | 0.491597 | different_skill | no | `db684279-fe2a-4b2b-b99d-e670560bab21` |
| 17 | 0.489960 | different_skill | no | `cd9946af-d6de-4b36-81f0-bd5f2b0ab8e4` |
| 18 | 0.489147 | different_skill | no | `c07c6f7e-97f0-4622-af88-60f9f48f1917` |
| 19 | 0.484543 | different_skill | no | `44352154-aaf6-46c4-92bf-78b8b002cd7d` |
| 20 | 0.465563 | different_skill | no | `762019fb-f182-4977-bf35-2d3aca5c7867` |

#### Describe the six benefits of cloud computing and the six perspectives of the AWS Cloud Adoption Framework (AWS CAF)

| Rank | Similarity | Label | Included at threshold | Content item |
|---:|---:|---|---|---|
| 1 | 0.740578 | same_skill | yes | `97fe17f2-7777-4202-9904-2e26011fa5fd` |
| 2 | 0.719518 | same_skill | yes | `ff8f8a77-7eb7-430b-bdf4-204993445b93` |
| 3 | 0.671079 | same_skill | yes | `3a384117-ff82-4819-b75d-fcf797900ca0` |
| 4 | 0.628607 | different_skill | yes | `c07c6f7e-97f0-4622-af88-60f9f48f1917` |
| 5 | 0.594106 | different_skill | yes | `60c97b8a-c2e5-4aa7-bf7c-f5755c6bcc1b` |
| 6 | 0.574141 | different_skill | yes | `64c9f7dd-b6ef-4d01-b399-e14a8ade4779` |
| 7 | 0.556372 | same_skill | yes | `6fb2bfba-1539-4c6f-a3cb-be23e59c9313` |
| 8 | 0.547492 | same_skill | yes | `272b5c6f-3e55-475b-8839-9670d894603c` |
| 9 | 0.537739 | different_skill | no | `b003b09d-9caf-4abb-b054-e50250b70f40` |
| 10 | 0.536736 | different_skill | no | `db684279-fe2a-4b2b-b99d-e670560bab21` |
| 11 | 0.530762 | different_skill | no | `4cae4811-6c9d-47f7-b49a-17e20f2c28d1` |
| 12 | 0.526315 | same_skill | no | `db641338-a1eb-41b6-b573-561b6de1264c` |
| 13 | 0.512849 | different_skill | no | `daaa80b2-5aff-4a9f-994f-43928d844668` |
| 14 | 0.504760 | different_skill | no | `44352154-aaf6-46c4-92bf-78b8b002cd7d` |
| 15 | 0.500715 | different_skill | no | `d7ac67f8-5e11-43bb-a7a0-9a38971556b2` |
| 16 | 0.475876 | different_skill | no | `14f69a3d-1954-48f7-ac9c-269293dd855e` |
| 17 | 0.468140 | different_skill | no | `f9de299c-5a3c-4821-a91e-465cc7f58d4b` |
| 18 | 0.467109 | different_skill | no | `4166c1c9-11b6-489e-9bff-1b55409a09de` |
| 19 | 0.459418 | different_skill | no | `43ba25e7-3dba-475a-8c19-6836fdd621b2` |
| 20 | 0.453211 | different_skill | no | `762019fb-f182-4977-bf35-2d3aca5c7867` |

#### Design a cloud architecture in AWS that satisfies scalability, high availability, and fault tolerance requirements

| Rank | Similarity | Label | Included at threshold | Content item |
|---:|---:|---|---|---|
| 1 | 0.759614 | same_skill | yes | `b003b09d-9caf-4abb-b054-e50250b70f40` |
| 2 | 0.581203 | different_skill | yes | `64c9f7dd-b6ef-4d01-b399-e14a8ade4779` |
| 3 | 0.544198 | different_skill | no | `fba4efe9-c749-4ccd-ac23-e6727ca566ae` |
| 4 | 0.530967 | different_skill | no | `d7ac67f8-5e11-43bb-a7a0-9a38971556b2` |
| 5 | 0.517602 | different_skill | no | `272b5c6f-3e55-475b-8839-9670d894603c` |
| 6 | 0.509759 | same_skill | no | `cd9946af-d6de-4b36-81f0-bd5f2b0ab8e4` |
| 7 | 0.497909 | different_skill | no | `f7771acf-459d-4b0a-9ad4-4cd3e37241d7` |
| 8 | 0.491011 | different_skill | no | `3a384117-ff82-4819-b75d-fcf797900ca0` |
| 9 | 0.480529 | different_skill | no | `c07c6f7e-97f0-4622-af88-60f9f48f1917` |
| 10 | 0.480453 | different_skill | no | `60c97b8a-c2e5-4aa7-bf7c-f5755c6bcc1b` |
| 11 | 0.475893 | different_skill | no | `b7d3ec4e-017a-4a23-9da5-def88254a5b6` |
| 12 | 0.472823 | different_skill | no | `44352154-aaf6-46c4-92bf-78b8b002cd7d` |
| 13 | 0.463946 | different_skill | no | `97fe17f2-7777-4202-9904-2e26011fa5fd` |
| 14 | 0.462710 | different_skill | no | `ff8f8a77-7eb7-430b-bdf4-204993445b93` |
| 15 | 0.458207 | different_skill | no | `c12c50b5-1228-492a-be48-63d478b6274c` |
| 16 | 0.458164 | different_skill | no | `6fb2bfba-1539-4c6f-a3cb-be23e59c9313` |
| 17 | 0.454794 | different_skill | no | `db641338-a1eb-41b6-b573-561b6de1264c` |
| 18 | 0.448087 | different_skill | no | `db684279-fe2a-4b2b-b99d-e670560bab21` |
| 19 | 0.446546 | different_skill | no | `0db88a11-eb83-4f6a-92ab-b6e2b1268944` |
| 20 | 0.440448 | different_skill | no | `78792d6d-05b3-4cf1-ab74-bfdc607d9eed` |

#### Configure auto scaling policies and CloudWatch monitoring to maintain reliability and cost efficiency

| Rank | Similarity | Label | Included at threshold | Content item |
|---:|---:|---|---|---|
| 1 | 0.755776 | same_skill | yes | `fba4efe9-c749-4ccd-ac23-e6727ca566ae` |
| 2 | 0.514215 | different_skill | no | `b003b09d-9caf-4abb-b054-e50250b70f40` |
| 3 | 0.512346 | same_skill | no | `44352154-aaf6-46c4-92bf-78b8b002cd7d` |
| 4 | 0.493369 | different_skill | no | `db641338-a1eb-41b6-b573-561b6de1264c` |
| 5 | 0.470099 | different_skill | no | `dbdca507-7596-4f42-b34b-e71134ed4d81` |
| 6 | 0.444775 | different_skill | no | `d7ac67f8-5e11-43bb-a7a0-9a38971556b2` |
| 7 | 0.439491 | different_skill | no | `272b5c6f-3e55-475b-8839-9670d894603c` |
| 8 | 0.430272 | different_skill | no | `64c9f7dd-b6ef-4d01-b399-e14a8ade4779` |
| 9 | 0.427823 | different_skill | no | `c07c6f7e-97f0-4622-af88-60f9f48f1917` |
| 10 | 0.427563 | different_skill | no | `b7d3ec4e-017a-4a23-9da5-def88254a5b6` |
| 11 | 0.419685 | different_skill | no | `f7771acf-459d-4b0a-9ad4-4cd3e37241d7` |
| 12 | 0.412150 | same_skill | no | `0db88a11-eb83-4f6a-92ab-b6e2b1268944` |
| 13 | 0.411742 | different_skill | no | `3a384117-ff82-4819-b75d-fcf797900ca0` |
| 14 | 0.402214 | different_skill | no | `6fb2bfba-1539-4c6f-a3cb-be23e59c9313` |
| 15 | 0.400990 | different_skill | no | `60c97b8a-c2e5-4aa7-bf7c-f5755c6bcc1b` |
| 16 | 0.399606 | different_skill | no | `ff8f8a77-7eb7-430b-bdf4-204993445b93` |
| 17 | 0.399293 | different_skill | no | `97fe17f2-7777-4202-9904-2e26011fa5fd` |
| 18 | 0.390643 | different_skill | no | `c12c50b5-1228-492a-be48-63d478b6274c` |
| 19 | 0.383445 | different_skill | no | `78792d6d-05b3-4cf1-ab74-bfdc607d9eed` |
| 20 | 0.383282 | different_skill | no | `db684279-fe2a-4b2b-b99d-e670560bab21` |

#### Compare managed AWS services against self-managed alternatives based on operational and cost trade-offs

| Rank | Similarity | Label | Included at threshold | Content item |
|---:|---:|---|---|---|
| 1 | 0.710510 | same_skill | yes | `dbdca507-7596-4f42-b34b-e71134ed4d81` |
| 2 | 0.568055 | different_skill | yes | `272b5c6f-3e55-475b-8839-9670d894603c` |
| 3 | 0.530421 | different_skill | no | `d7ac67f8-5e11-43bb-a7a0-9a38971556b2` |
| 4 | 0.521858 | different_skill | no | `fba4efe9-c749-4ccd-ac23-e6727ca566ae` |
| 5 | 0.513574 | different_skill | no | `c07c6f7e-97f0-4622-af88-60f9f48f1917` |
| 6 | 0.509445 | different_skill | no | `ff8f8a77-7eb7-430b-bdf4-204993445b93` |
| 7 | 0.489029 | different_skill | no | `b003b09d-9caf-4abb-b054-e50250b70f40` |
| 8 | 0.480132 | different_skill | no | `3a384117-ff82-4819-b75d-fcf797900ca0` |
| 9 | 0.479736 | different_skill | no | `97fe17f2-7777-4202-9904-2e26011fa5fd` |
| 10 | 0.479344 | different_skill | no | `b7d3ec4e-017a-4a23-9da5-def88254a5b6` |
| 11 | 0.478051 | different_skill | no | `db641338-a1eb-41b6-b573-561b6de1264c` |
| 12 | 0.477712 | different_skill | no | `f7771acf-459d-4b0a-9ad4-4cd3e37241d7` |
| 13 | 0.470739 | different_skill | no | `c12c50b5-1228-492a-be48-63d478b6274c` |
| 14 | 0.467498 | different_skill | no | `64c9f7dd-b6ef-4d01-b399-e14a8ade4779` |
| 15 | 0.466701 | different_skill | no | `6fb2bfba-1539-4c6f-a3cb-be23e59c9313` |
| 16 | 0.453922 | different_skill | no | `44352154-aaf6-46c4-92bf-78b8b002cd7d` |
| 17 | 0.441502 | different_skill | no | `14f69a3d-1954-48f7-ac9c-269293dd855e` |
| 18 | 0.439100 | different_skill | no | `78792d6d-05b3-4cf1-ab74-bfdc607d9eed` |
| 19 | 0.424195 | different_skill | no | `daaa80b2-5aff-4a9f-994f-43928d844668` |
| 20 | 0.423883 | different_skill | no | `0db88a11-eb83-4f6a-92ab-b6e2b1268944` |

#### Identify AWS certification pathways and credential requirements

| Rank | Similarity | Label | Included at threshold | Content item |
|---:|---:|---|---|---|
| 1 | 0.692312 | same_skill | yes | `762019fb-f182-4977-bf35-2d3aca5c7867` |
| 2 | 0.598120 | same_skill | yes | `fce62b14-bb45-441c-b13e-73aeb8b79bb2` |
| 3 | 0.577367 | different_skill | yes | `44352154-aaf6-46c4-92bf-78b8b002cd7d` |
| 4 | 0.574666 | same_skill | yes | `4166c1c9-11b6-489e-9bff-1b55409a09de` |
| 5 | 0.571322 | same_skill | yes | `43ba25e7-3dba-475a-8c19-6836fdd621b2` |
| 6 | 0.567367 | same_skill | yes | `db684279-fe2a-4b2b-b99d-e670560bab21` |
| 7 | 0.564831 | same_skill | yes | `14f69a3d-1954-48f7-ac9c-269293dd855e` |
| 8 | 0.562384 | same_skill | yes | `4faf69ac-d2ff-4eb8-8815-e971fe6837e3` |
| 9 | 0.559381 | same_skill | yes | `f9de299c-5a3c-4821-a91e-465cc7f58d4b` |
| 10 | 0.544897 | same_skill | yes | `daaa80b2-5aff-4a9f-994f-43928d844668` |
| 11 | 0.525975 | same_skill | no | `4cae4811-6c9d-47f7-b49a-17e20f2c28d1` |
| 12 | 0.521906 | different_skill | no | `c95cd856-8ade-4bca-bc35-8d2d0cdf7bd4` |
| 13 | 0.511214 | different_skill | no | `ff8f8a77-7eb7-430b-bdf4-204993445b93` |
| 14 | 0.503231 | different_skill | no | `d7ac67f8-5e11-43bb-a7a0-9a38971556b2` |
| 15 | 0.493909 | different_skill | no | `97fe17f2-7777-4202-9904-2e26011fa5fd` |
| 16 | 0.476794 | different_skill | no | `64c9f7dd-b6ef-4d01-b399-e14a8ade4779` |
| 17 | 0.474480 | different_skill | no | `3a384117-ff82-4819-b75d-fcf797900ca0` |
| 18 | 0.471041 | different_skill | no | `272b5c6f-3e55-475b-8839-9670d894603c` |
| 19 | 0.467070 | different_skill | no | `b14d6e5e-9a7c-497a-a9ac-22dd12138076` |
| 20 | 0.463151 | different_skill | no | `0db88a11-eb83-4f6a-92ab-b6e2b1268944` |

#### Compile course deliverables for AWS course badge submission

| Rank | Similarity | Label | Included at threshold | Content item |
|---:|---:|---|---|---|
| 1 | 0.662876 | same_skill | yes | `b14d6e5e-9a7c-497a-a9ac-22dd12138076` |
| 2 | 0.641184 | same_skill | yes | `c95cd856-8ade-4bca-bc35-8d2d0cdf7bd4` |
| 3 | 0.612070 | different_skill | yes | `fce62b14-bb45-441c-b13e-73aeb8b79bb2` |
| 4 | 0.583929 | different_skill | yes | `daaa80b2-5aff-4a9f-994f-43928d844668` |
| 5 | 0.580750 | different_skill | yes | `43ba25e7-3dba-475a-8c19-6836fdd621b2` |
| 6 | 0.567127 | different_skill | yes | `f9de299c-5a3c-4821-a91e-465cc7f58d4b` |
| 7 | 0.562609 | different_skill | yes | `db684279-fe2a-4b2b-b99d-e670560bab21` |
| 8 | 0.561315 | different_skill | yes | `44352154-aaf6-46c4-92bf-78b8b002cd7d` |
| 9 | 0.552551 | different_skill | yes | `4faf69ac-d2ff-4eb8-8815-e971fe6837e3` |
| 10 | 0.547799 | same_skill | yes | `f0ee751c-49d1-410f-9ec8-f6a1ffba4e22` |
| 11 | 0.540963 | different_skill | no | `14f69a3d-1954-48f7-ac9c-269293dd855e` |
| 12 | 0.535800 | different_skill | no | `4166c1c9-11b6-489e-9bff-1b55409a09de` |
| 13 | 0.529469 | different_skill | no | `4cae4811-6c9d-47f7-b49a-17e20f2c28d1` |
| 14 | 0.517413 | different_skill | no | `762019fb-f182-4977-bf35-2d3aca5c7867` |
| 15 | 0.484630 | null_skill | no | `1385dfe2-9a02-43e0-aa71-4c1519f742c9` |
| 16 | 0.468434 | different_skill | no | `0db88a11-eb83-4f6a-92ab-b6e2b1268944` |
| 17 | 0.458118 | different_skill | no | `d7ac67f8-5e11-43bb-a7a0-9a38971556b2` |
| 18 | 0.451429 | different_skill | no | `6fb2bfba-1539-4c6f-a3cb-be23e59c9313` |
| 19 | 0.441934 | same_skill | no | `e5183d43-6b6a-428a-b504-1e9725ed8a91` |
| 20 | 0.440550 | null_skill | no | `56f2c01e-ffe7-41af-b3da-a32911e11898` |

#### Evaluate personal readiness for AWS Cloud Practitioner certification

| Rank | Similarity | Label | Included at threshold | Content item |
|---:|---:|---|---|---|
| 1 | 0.657607 | different_skill | yes | `762019fb-f182-4977-bf35-2d3aca5c7867` |
| 2 | 0.611434 | different_skill | yes | `44352154-aaf6-46c4-92bf-78b8b002cd7d` |
| 3 | 0.588046 | different_skill | yes | `daaa80b2-5aff-4a9f-994f-43928d844668` |
| 4 | 0.586769 | different_skill | yes | `fce62b14-bb45-441c-b13e-73aeb8b79bb2` |
| 5 | 0.585914 | different_skill | yes | `14f69a3d-1954-48f7-ac9c-269293dd855e` |
| 6 | 0.570880 | different_skill | yes | `4cae4811-6c9d-47f7-b49a-17e20f2c28d1` |
| 7 | 0.564354 | different_skill | yes | `4166c1c9-11b6-489e-9bff-1b55409a09de` |
| 8 | 0.562185 | different_skill | yes | `db684279-fe2a-4b2b-b99d-e670560bab21` |
| 9 | 0.561118 | different_skill | yes | `c95cd856-8ade-4bca-bc35-8d2d0cdf7bd4` |
| 10 | 0.544381 | different_skill | no | `0db88a11-eb83-4f6a-92ab-b6e2b1268944` |
| 11 | 0.530508 | different_skill | no | `97fe17f2-7777-4202-9904-2e26011fa5fd` |
| 12 | 0.530093 | different_skill | no | `f9de299c-5a3c-4821-a91e-465cc7f58d4b` |
| 13 | 0.524142 | different_skill | no | `4faf69ac-d2ff-4eb8-8815-e971fe6837e3` |
| 14 | 0.518705 | different_skill | no | `ff8f8a77-7eb7-430b-bdf4-204993445b93` |
| 15 | 0.516599 | different_skill | no | `6fb2bfba-1539-4c6f-a3cb-be23e59c9313` |
| 16 | 0.513442 | same_skill | no | `320fad40-3f43-46e0-915f-d3e0d43aa0c4` |
| 17 | 0.510949 | different_skill | no | `43ba25e7-3dba-475a-8c19-6836fdd621b2` |
| 18 | 0.488373 | null_skill | no | `56f2c01e-ffe7-41af-b3da-a32911e11898` |
| 19 | 0.485662 | different_skill | no | `3a384117-ff82-4819-b75d-fcf797900ca0` |
| 20 | 0.485068 | different_skill | no | `b14d6e5e-9a7c-497a-a9ac-22dd12138076` |

### Similarity distribution

| Label | Count | Min | Median | P95 | Max |
|---|---:|---:|---:|---:|---:|
| same_skill | 35 | 0.412150260598149 | 0.567367412248491 | 0.7451371184330119 | 0.759613535088279 |
| different_skill | 160 | 0.358986383850942 | 0.4825360567946775 | 0.5868327615858893 | 0.657607133009282 |
| null_skill | 5 | 0.369445847816466 | 0.440550248093015 | 0.48762448979010337 | 0.488373109842779 |

### Threshold examples

Examples are capped to the first 150 characters as requested.

| Side | Skill | Similarity | Label | Example |
|---|---|---:|---|---|
| above | Compare and contrast traditional IT infrastructure with cloud computing models | 0.546931 | different_skill | Module 1: Cloud Concepts Overview introduces the basic ideas of cloud computing and the value of Amazon Web Services (AWS). Cloud computing means usin |
| above | Compare and contrast traditional IT infrastructure with cloud computing models | 0.574678 | different_skill | The Cloud Concepts Overview introduces the fundamental benefits of cloud computing, including scalability, flexibility, and pay-as-you-go pricing. It  |
| above | Compare and contrast traditional IT infrastructure with cloud computing models | 0.590779 | different_skill | © 2022, Amazon Web Services, Inc. or its affiliates. All rights reserved. Module 1: Cloud Concepts Overview AWS Academy Cloud Foundations © 2022, Amaz |
| below | Compare and contrast traditional IT infrastructure with cloud computing models | 0.521082 | different_skill | ses align IT strategy  and goals with business strategy and goals so the  organization can maximize the business value of its IT  investment and minim |
| below | Compare and contrast traditional IT infrastructure with cloud computing models | 0.487702 | different_skill | Cloud Architecture in AWS focuses on designing systems that are scalable, reliable, and cost-efficient. It emphasizes best practices such as high avai |
| below | Compare and contrast traditional IT infrastructure with cloud computing models | 0.476379 | different_skill | All rights reserved. 15 Trade capital expense for variable expense Data center investment  based on forecast Capital Pay only for the amount  you cons |

## Batch generation

| Batch | max_tokens | Runs | Successful runs | p50 latency | p95 latency | Validator pass rate | Avg returned | Near-duplicate batches |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 4096 | 15 | 12 | 117279 ms | 205200 ms | 100.0% | 3.67 | 3 |
| 5 | 8192 | 15 | 12 | 62907 ms | 214413 ms | 98.3% | 4.00 | 0 |
| 8 | 8192 | 9 | 9 | 94082 ms | 199213 ms | 98.4% | 7.11 | 0 |

### Schema probe

| Schema | HTTP accepted | Parsed items | Validator-passing items | Finish reason |
|---|---|---:|---:|---|
| array | yes | 5 | 5 | stop |
| wrapper | yes | 5 | 5 | stop |

## Concurrency

| Concurrent calls | Wall time | Latency min / median / max | 429s | Errors |
|---:|---:|---|---:|---:|
| 2 | 98989 ms | 52056 / 75521.5 / 98987 ms | 0 | 0 |
| 4 | 199309 ms | 58372 / 150356.0 / 199304 ms | 0 | 0 |

## Verification

- `generated_items.source_chunk_ids` is written by the lesson shell in `services/api/app/learn/lessons.py:255-270`; the item generators at `services/api/app/learn/items.py:390-403` and `services/worker/app/item_gen.py:292-306` do not populate it.
- The flashcard deck query does **not** filter `generated_items.kind`; `services/api/app/routers/flashcards.py:100-104` and `:169-173` filter by item IDs only.


## Recommendations

- `SIM_THRESHOLD`: **0.544381** for this measured union; review/retag the cross-skill rows before treating similarity alone as ground truth.
- `MCQ_BATCH`: **5**. Batch 8 returned only 7.11 items on average, versus the requested 8, with no latency advantage.
- `max_tokens`: **8192**. It removed the near-duplicate batches seen at 4096 (0 versus 3), while validator pass rate remained 98.3%; it is still slow (5-item p95 214.4s).
- `BANK_CONCURRENCY`: **2**. Two-way wall time was 99.0s; four-way wall time doubled to 199.3s. Neither produced a 429, but four-way provides no throughput benefit in this run.
- Build-time estimates use the measured 5-item/8192 p95, 2-way concurrency, and 10 approved skills; they are estimates, not production measurements.

- Estimated AWS101 timing: **3 batches / 5.4 minutes to MIN_USABLE (5 per skill)** and **149 batches / 4.4 hours to 80 per skill**, assuming 5 MCQs per successful batch, 8192 max tokens, 2-way concurrency, and the measured 214.4s p95. Actual time may be longer because failed/partial batches and provider throttling are excluded.
- Live verification found **0** in-progress AWS101 practice jobs at query time, so there were no `started_at`/`updated_at` pairs to classify as stale.
