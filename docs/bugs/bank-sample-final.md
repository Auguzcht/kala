# AWS101 final live bank sample — 2026-10-06

Course: `ae4e7680-f94b-4652-b3f6-b9c32f4420de`  
Three random live items per ready skill. `retired_at` is null for every item.

## Compare and contrast traditional IT infrastructure with cloud computing models

1. **Bloom:** analyze  
   **Stem:** A company is comparing traditional IT and cloud. In traditional IT, they had to wait weeks for physical hardware to be procured and installed. In cloud, they can launch resources in minutes. Which cloud advantage does this describe?  
   **Choices:** a) Trade capital expense for variable expense; b) Benefit from massive economies of scale; c) Stop guessing capacity; d) Increase speed and agility.  
   **Correct:** d. **Explanation:** Cloud resources can be launched in minutes, improving speed and agility.

2. **Bloom:** analyze  
   **Stem:** A development team wants to manage AWS services programmatically from within a Python application, calling AWS APIs directly from code. Which AWS management method should they use?  
   **Choices:** a) AWS Management Console; b) AWS CLI; c) Software Development Kits (SDKs); d) AWS CloudFormation.  
   **Correct:** c. **Explanation:** SDKs enable programmatic API calls from languages such as Python and Java.

3. **Bloom:** analyze  
   **Stem:** A global retail company wants to deploy its application to customers in North America, Europe, and Asia without building physical data centers in each region. Which cloud benefit directly enables this?  
   **Choices:** a) Trade capital expense for variable expense; b) Benefit from massive economies of scale; c) Stop guessing capacity; d) Go global in minutes.  
   **Correct:** d. **Explanation:** AWS supports global deployment without requiring physical data centers in every region.

## Compare managed AWS services against self-managed alternatives based on operational and cost trade-offs

1. **Bloom:** evaluate  
   **Stem:** A company has a workload that fluctuates significantly throughout the day. They have a large operations team skilled in managing servers and want to maintain control over the underlying infrastructure. They are willing to invest in automation to handle scaling. Which approach best fits their situation?  
   **Choices:** a) AWS Lambda; b) Amazon EC2 with auto scaling groups managed by their operations team; c) Amazon ECS with Fargate; d) AWS Elastic Beanstalk.  
   **Correct:** b. **Explanation:** Self-managed EC2 preserves infrastructure control while accepting operational responsibility.

2. **Bloom:** evaluate  
   **Stem:** A company has a steady, predictable database workload but no dedicated database administration team. They want to minimize operational overhead and are willing to pay higher per-unit costs. Which approach best aligns with their priorities?  
   **Choices:** a) A managed database service; b) A self-managed database on EC2; c) A self-managed on-premises database; d) A managed database with no per-unit costs.  
   **Correct:** a. **Explanation:** Managed services trade higher per-unit cost for reduced operational overhead.

3. **Bloom:** evaluate  
   **Stem:** A development team is comparing AWS Lambda and Amazon EC2 for a new application with unpredictable traffic. They have a large operations team that is skilled in server management and wants to minimize direct costs. Which evaluation best captures the trade-off?  
   **Choices:** a) Lambda reduces management while EC2 can be cheaper for steady high-volume workloads; b) Lambda always costs less; c) EC2 requires no operational effort; d) Both have identical cost and overhead.  
   **Correct:** a. **Explanation:** Lambda reduces operations; EC2 can reduce direct cost when managed by an experienced team.

## Compile course deliverables for AWS course badge submission

1. **Bloom:** apply  
   **Stem:** A student is assigned a hands-on lab in which they must build a virtual private cloud and launch a web server. Which module contains this lab?  
   **Choices:** a) Global Infrastructure Overview; b) Cloud Security; c) Networking and Content Delivery; d) Compute.  
   **Correct:** c. **Explanation:** VPC and web-server networking work belongs to Networking and Content Delivery.

2. **Bloom:** apply  
   **Stem:** A student needs to learn how to create a virtual private cloud using Amazon VPC. Which topic area covers this?  
   **Choices:** a) Networking and Content Delivery; b) Compute; c) Storage; d) Cloud Security.  
   **Correct:** a. **Explanation:** Amazon VPC is covered by Networking and Content Delivery.

3. **Bloom:** apply  
   **Stem:** A developer is following a serverless Hello World tutorial. Which two AWS services does it use?  
   **Choices:** a) AWS Lambda and Amazon CloudWatch; b) EC2 and S3; c) Elastic Beanstalk and RDS; d) VPC and Route 53.  
   **Correct:** a. **Explanation:** The tutorial uses Lambda and CloudWatch.

## Describe the six benefits of cloud computing and the six perspectives of the AWS CAF

1. **Bloom:** remember  
   **Stem:** Which of the following is NOT one of the six benefits of cloud computing?  
   **Choices:** a) Increased security through automatic patching; b) Trade capital expense for variable expense; c) Benefit from massive economies of scale; d) Stop guessing about capacity.  
   **Correct:** a. **Explanation:** Automatic patching is not one of the six listed benefits.

2. **Bloom:** remember  
   **Stem:** Which cloud computing benefit addresses overestimating or underestimating server capacity?  
   **Choices:** a) Increase speed and agility; b) Stop guessing capacity; c) Trade capital expense for variable expense; d) Benefit from massive economies of scale.  
   **Correct:** b. **Explanation:** On-demand scaling avoids guessing peak capacity.

3. **Bloom:** remember  
   **Stem:** Which AWS CAF perspective includes identity and access management, detective control, and incident response?  
   **Choices:** a) Business; b) Platform; c) Security; d) Operations.  
   **Correct:** c. **Explanation:** These capabilities belong to the Security perspective.

## Evaluate personal readiness for AWS Cloud Practitioner certification

1. **Bloom:** evaluate  
   **Stem:** A learner wants the exam content domains, question types, and logistics for the Cloud Practitioner exam. Which resource should they consult first?  
   **Choices:** a) AWS Certified Cloud Practitioner Exam Guide; b) AWS Documentation; c) Recommended AWS whitepapers; d) Cloud Foundations course topics.  
   **Correct:** a. **Explanation:** The exam guide covers exam content and logistics.

2. **Bloom:** evaluate  
   **Stem:** A learner has earned Cloud Practitioner and wants to plan advanced certifications. What foundation does AWS Academy Cloud Foundations provide?  
   **Choices:** a) A foundation for Associate, Professional, and Specialty certifications; b) Only Cloud Practitioner preparation; c) Automatic advanced certifications; d) Technical-role preparation only.  
   **Correct:** a. **Explanation:** The course provides foundational knowledge for advanced certification paths.

3. **Bloom:** evaluate  
   **Stem:** A learner wants to validate foundational, high-level understanding of AWS Cloud, services, and terminology. Which certification should they pursue?  
   **Choices:** a) AWS Certified Cloud Practitioner; b) Solutions Architect Associate; c) SysOps Administrator Associate; d) Data Engineer Associate.  
   **Correct:** a. **Explanation:** Cloud Practitioner validates foundational AWS knowledge.

## Identify appropriate AWS service categories for given business requirements

1. **Bloom:** apply  
   **Stem:** An application needs a fully managed NoSQL database that can scale to millions of requests per second. Which AWS service category should it use?  
   **Choices:** a) Compute; b) Storage; c) Database; d) Networking.  
   **Correct:** c. **Explanation:** DynamoDB belongs to the Database category.

2. **Bloom:** apply  
   **Stem:** A company wants to launch and manage a virtual private server with a simplified interface and preconfigured stack. Which category applies?  
   **Choices:** a) Compute; b) Storage; c) Database; d) Networking.  
   **Correct:** a. **Explanation:** Amazon Lightsail is a Compute service.

3. **Bloom:** apply  
   **Stem:** A company needs shared file storage that multiple Linux EC2 instances can access simultaneously. Which category applies?  
   **Choices:** a) Compute; b) Database; c) Storage; d) Networking.  
   **Correct:** c. **Explanation:** Amazon EFS is shared file storage.

## Identify the purpose and primary use cases of core AWS compute, storage, and database services

1. **Bloom:** remember  
   **Stem:** What do Amazon RDS and Amazon DynamoDB enable users to do?  
   **Choices:** a) Run relational and NoSQL databases without managing infrastructure; b) Run containers without servers; c) Store objects; d) Manage network traffic.  
   **Correct:** a. **Explanation:** RDS and DynamoDB provide managed relational and NoSQL databases.

2. **Bloom:** remember  
   **Stem:** Which pair of AWS services are used for storage?  
   **Choices:** a) EC2 and Lambda; b) S3 and EBS; c) RDS and DynamoDB; d) VPC and Route 53.  
   **Correct:** b. **Explanation:** S3 and EBS are AWS storage services.

3. **Bloom:** remember  
   **Stem:** What is the primary purpose of Amazon S3?  
   **Choices:** a) Store and manage data at scale; b) Run virtual servers; c) Manage relational databases; d) Deliver content globally.  
   **Correct:** a. **Explanation:** S3 securely stores and manages objects at scale.
