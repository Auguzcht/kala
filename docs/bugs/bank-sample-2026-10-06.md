# AWS101 bank item review sample — 2026-10-06

Course: `ae4e7680-f94b-4652-b3f6-b9c32f4420de`  
Read-only export of 30 randomly selected live items, spread across available skills. Correct choices are marked explicitly for reviewer use.

## 1. Compare managed AWS services against self-managed alternatives based on operational and cost trade-offs

- Bloom: `evaluate`
- Item ID: `437e941b-f5c3-495c-a934-ccc5317fed59`
- Stem: A company runs a nightly batch processing job that takes several hours. They have a team of system administrators who are experienced in managing servers. The company wants to minimize direct costs and is willing to handle patching, scaling, and maintenance themselves. Which approach best aligns with their priorities?
- Choices:
- **a** Use AWS Lambda to run the batch job, paying only for the compute time consumed.
- **b** Use Amazon EC2 instances that the team manages, stopping them when the job is not running.
- **c** Use a fully managed container service that automatically handles scaling and patching.
- **d** Use AWS Elastic Beanstalk to deploy and manage the application automatically.
- Correct choice: **b**
- Explanation: Self-managed alternatives like Amazon EC2 trade lower direct cost for more operational responsibility and control. Since the company has an experienced team and wants to minimize costs while accepting maintenance tasks, managing EC2 instances themselves aligns with that trade-off. Managed services like Lambda or Elastic Beanstalk reduce operational overhead but typically have higher per-unit costs.

## 2. Compare managed AWS services against self-managed alternatives based on operational and cost trade-offs

- Bloom: `evaluate`
- Item ID: `891cf87f-abce-47b6-a6cd-98d00b804c18`
- Stem: A development team is comparing AWS Lambda and Amazon EC2 for a new application with unpredictable traffic. They have a large operations team that is skilled in server management and wants to minimize direct costs. Which evaluation best captures the trade-off between these two options?
- Choices:
- **a** Lambda is better because it eliminates server management, but EC2 is better because it can be cheaper for steady, high-volume workloads when you have operations staff.
- **b** Lambda is better because it always costs less than EC2 for any workload.
- **c** EC2 is better because it requires no operational effort, while Lambda requires patching.
- **d** Both are identical in cost and operational overhead, so the choice depends only on programming language.
- Correct choice: **a**
- Explanation: AWS Lambda reduces operational overhead but may have higher per-unit cost; Amazon EC2 can be cheaper for steady, high-volume workloads if you have operations staff to manage it. The trade-off is operational overhead versus direct cost.

## 3. Compare managed AWS services against self-managed alternatives based on operational and cost trade-offs

- Bloom: `evaluate`
- Item ID: `3fbcfa85-93d7-4835-88ee-1859ee20293d`
- Stem: A company has a steady, predictable workload and a large operations team skilled in server management. They want to minimize direct costs and are willing to take on more operational responsibility. Which approach best aligns with this goal?
- Choices:
- **a** AWS Lambda, because it eliminates server provisioning and management.
- **b** Amazon EC2, because it provides resizable virtual servers that the company manages itself.
- **c** A fully managed AWS database service, because it reduces operational overhead.
- **d** AWS Outposts, because it extends AWS infrastructure on premises.
- Correct choice: **b**
- Explanation: Self-managed alternatives like EC2 trade lower direct cost for more operational responsibility and control. Lambda and managed services reduce overhead but may have higher per-unit cost.

## 4. Compare managed AWS services against self-managed alternatives based on operational and cost trade-offs

- Bloom: `evaluate`
- Item ID: `ca3e981b-44c0-429e-8e33-b28fa52a55a9`
- Stem: A company has a steady, predictable database workload. They employ a dedicated database administration team. The company wants full control over database configuration and aims to minimize licensing and hosting costs. Which approach best aligns with their goals?
- Choices:
- **a** Use a fully managed database service that handles patching and backups.
- **b** Run a self-managed database on Amazon EC2 instances.
- **c** Use a fully managed NoSQL database service that scales automatically.
- **d** Use a serverless database that charges per request.
- Correct choice: **b**
- Explanation: Self-managed alternatives trade lower direct cost for more operational responsibility and control. With a dedicated DBA team and a desire for full control and cost minimization, running a self-managed database on EC2 fits the trade-off. Managed database services reduce operational overhead but typically cost more per unit.

## 5. Compare managed AWS services against self-managed alternatives based on operational and cost trade-offs

- Bloom: `evaluate`
- Item ID: `b8414fcc-9a25-4566-bd7f-8b5f2170bc06`
- Stem: A company has a steady, predictable database workload but no dedicated database administration team. They want to minimize operational overhead and are willing to pay higher per-unit costs. Which approach best aligns with their priorities?
- Choices:
- **a** A managed database service, because it reduces operational overhead at the cost of higher per-unit pricing.
- **b** A self-managed database on Amazon EC2, because it lowers direct costs and gives full control.
- **c** A self-managed database on-premises, because it avoids all cloud costs.
- **d** A managed database service, because it eliminates all per-unit costs.
- Correct choice: **a**
- Explanation: Managed services trade higher per-unit cost for reduced operational overhead; self-managed alternatives trade lower direct cost for more operational responsibility. Since the company lacks a DBA team and wants to minimize overhead, a managed database service is the better fit.

## 6. Compare managed AWS services against self-managed alternatives based on operational and cost trade-offs

- Bloom: `evaluate`
- Item ID: `e961d4fc-e53a-41ce-8fc3-aa9b0f4a50a8`
- Stem: A business currently invests in data center hardware based on forecasted demand. They want to shift to a model where they pay only for what they consume. Which AWS cloud benefit does this describe?
- Choices:
- **a** Increase speed and agility.
- **b** Stop spending money on running and maintaining data centers.
- **c** Trade capital expense for variable expense.
- **d** Benefit from massive economies of scale.
- Correct choice: **c**
- Explanation: Trading capital expense for variable expense means replacing data center investment based on forecast with paying only for the amount consumed.

## 7. Compare managed AWS services against self-managed alternatives based on operational and cost trade-offs

- Bloom: `evaluate`
- Item ID: `6a3811a7-a107-4436-be57-fcf46e64a083`
- Stem: A small startup needs to deploy a simple API. The team has no dedicated operations staff and expects traffic to vary unpredictably. They want to minimize operational overhead even if per-unit costs are higher. Which AWS service choice best matches this trade-off?
- Choices:
- **a** Amazon EC2 instances, because they provide resizable virtual servers with lower direct cost.
- **b** AWS Lambda, because it runs code without provisioning servers and reduces operational overhead.
- **c** A self-managed database on Amazon EC2, because it offers more control.
- **d** An on-premises data center, because it avoids cloud per-unit costs.
- Correct choice: **b**
- Explanation: AWS Lambda runs code without provisioning servers, trading higher per-unit cost for reduced operational overhead. EC2 and self-managed options require more operational responsibility.

## 8. Compare managed AWS services against self-managed alternatives based on operational and cost trade-offs

- Bloom: `evaluate`
- Item ID: `02482250-e80e-4206-a38c-af6f7cbde946`
- Stem: A company is migrating a legacy application that requires custom kernel modules and specific OS-level configurations. They have a skilled operations team and want to minimize direct costs. Which approach best aligns with their needs?
- Choices:
- **a** A managed AWS service, because it provides the most control over the underlying infrastructure.
- **b** A self-managed solution on Amazon EC2, because it offers more control and lower direct costs, though it requires more operational responsibility.
- **c** A serverless service like AWS Lambda, because it allows custom kernel modules.
- **d** A managed database service, because it handles all OS-level configurations.
- Correct choice: **b**
- Explanation: Self-managed alternatives trade lower direct cost for more operational responsibility and control. Since the application needs custom kernel modules and the company has a skilled team, a self-managed solution on Amazon EC2 is appropriate. Managed services may not allow such customization.

## 9. Compile course deliverables for AWS course badge submission

- Bloom: `apply`
- Item ID: `634377dd-a264-4ffe-8919-a165ae9711c0`
- Stem: A developer is following an AWS tutorial to run a serverless Hello World application. Which two AWS services does the tutorial have them use?
- Choices:
- **a** AWS Lambda and Amazon CloudWatch
- **b** Amazon EC2 and Amazon S3
- **c** AWS Elastic Beanstalk and Amazon RDS
- **d** Amazon VPC and Amazon Route 53
- Correct choice: **a**
- Explanation: The serverless Hello World tutorial instructs users to use AWS Lambda and Amazon CloudWatch.

## 10. Compile course deliverables for AWS course badge submission

- Bloom: `apply`
- Item ID: `38b059e4-a1d1-4acd-a4cf-89d650776ab2`
- Stem: A cloud engineer needs to create an Amazon S3 bucket and wants to follow the official AWS instructions. Starting from the AWS website, what is the correct sequence of steps to find the instructions for creating an Amazon S3 bucket?
- Choices:
- **a** Click S3, then click Getting Started Guide, then click Create a Bucket.
- **b** Click S3, then click API Reference, then click Create a Bucket.
- **c** Click S3, then click User Guide, then click Create a Bucket.
- **d** Click S3, then click Developer Guide, then click Create a Bucket.
- Correct choice: **a**
- Explanation: To create an Amazon S3 bucket, the instructions are found by clicking S3, then Getting Started Guide, then Create a Bucket.

## 11. Compile course deliverables for AWS course badge submission

- Bloom: `apply`
- Item ID: `547bc0e6-ec7a-450e-a9d8-3b1f036e8c85`
- Stem: A solutions architect is deciding whether to deploy a workload on a virtual server, a serverless function, or a platform-as-a-service environment. Which learning objective from the AWS Academy Cloud Foundations course directly addresses this decision?
- Choices:
- **a** Demonstrate when to use Amazon EC2, AWS Lambda, and AWS Elastic Beanstalk
- **b** Differentiate between Amazon S3, Amazon EBS, Amazon EFS, and Amazon S3 Glacier
- **c** Demonstrate when to use AWS database services, including Amazon RDS, Amazon DynamoDB, Amazon Redshift, and Amazon Aurora
- **d** Create a virtual private cloud (VPC) by using Amazon Virtual Private Cloud (Amazon VPC)
- Correct choice: **a**
- Explanation: The course objective 'Demonstrate when to use Amazon EC2, AWS Lambda, and AWS Elastic Beanstalk' covers choosing between virtual servers, serverless functions, and platform-as-a-service.

## 12. Compile course deliverables for AWS course badge submission

- Bloom: `apply`
- Item ID: `5c2e284c-ed7d-43bf-a868-c25079de656a`
- Stem: A learner wants to understand how an organization moves to the AWS Cloud by using the AWS Cloud Adoption Framework (AWS CAF). Which module covers this topic?
- Choices:
- **a** Module 1: Cloud Concepts Overview
- **b** Module 5: Networking and Content Delivery
- **c** Module 9: Cloud Architecture
- **d** Module 10: Automatic Scaling and Monitoring
- Correct choice: **a**
- Explanation: Module 1: Cloud Concepts Overview includes the section 'Moving to the AWS Cloud – The AWS Cloud Adoption Framework (AWS CAF).'

## 13. Compile course deliverables for AWS course badge submission

- Bloom: `apply`
- Item ID: `c96f9daa-b74c-4d5f-a06f-cc47c305366c`
- Stem: A student needs to learn how to create a virtual private cloud (VPC) using Amazon Virtual Private Cloud. Which topic area of the AWS Academy Cloud Foundations course covers this?
- Choices:
- **a** Networking and Content Delivery
- **b** Compute
- **c** Storage
- **d** Cloud Security
- Correct choice: **a**
- Explanation: The Networking and Content Delivery topic area includes Amazon VPC and VPC networking, where students learn to create a VPC.

## 14. Compile course deliverables for AWS course badge submission

- Bloom: `apply`
- Item ID: `239a9ea8-6072-4ab8-a997-ec983de9d5a0`
- Stem: A learner wants to understand the AWS shared responsibility model and how to secure a new AWS account. Which topic area of the AWS Academy Cloud Foundations course should they focus on?
- Choices:
- **a** Cloud Security
- **b** Cloud Concepts
- **c** Cloud Economics and Billing
- **d** AWS Global Infrastructure
- Correct choice: **a**
- Explanation: The Cloud Security topic area covers the AWS shared responsibility model, securing a new AWS account, and AWS IAM.

## 15. Compile course deliverables for AWS course badge submission

- Bloom: `apply`
- Item ID: `7543c5d0-ae2e-461f-9bd9-66fa1af8de6c`
- Stem: A student needs to understand AWS Organizations, AWS Billing and Cost Management, and the available technical support models. Which module covers these topics?
- Choices:
- **a** Module 2: Cloud Economics and Billing
- **b** Module 3: AWS Global Infrastructure Overview
- **c** Module 4: AWS Cloud Security
- **d** Module 8: Databases
- Correct choice: **a**
- Explanation: Module 2: Cloud Economics and Billing includes AWS Organizations, AWS Billing and Cost Management, and technical support.

## 16. Compile course deliverables for AWS course badge submission

- Bloom: `apply`
- Item ID: `77cb36db-42cd-4ce0-b5c1-8889803a97ef`
- Stem: A learner wants to explore key concepts related to Elastic Load Balancing, Amazon CloudWatch, and Amazon EC2 Auto Scaling. Which module should they study?
- Choices:
- **a** Module 6: Compute
- **b** Module 9: Cloud Architecture
- **c** Module 10: Automatic Scaling and Monitoring
- **d** Module 2: Cloud Economics and Billing
- Correct choice: **c**
- Explanation: Module 10: Automatic Scaling and Monitoring covers key concepts related to Elastic Load Balancing, Amazon CloudWatch, and Amazon EC2 Auto Scaling.

## 17. Design a cloud architecture in AWS that satisfies scalability, high availability, and fault tolerance requirements

- Bloom: `create`
- Item ID: `ab061119-bba5-45b6-9199-6a08367b8423`
- Stem: A company wants to design a cloud architecture that is both scalable and cost-efficient. Which approach best aligns with AWS best practices for achieving these goals?
- Choices:
- **a** Use managed services and Auto Scaling to match capacity to demand
- **b** Over-provision resources to handle peak load at all times
- **c** Use only on-demand instances for all workloads regardless of usage patterns
- **d** Manually scale resources based on historical averages
- Correct choice: **a**
- Explanation: Managed services reduce operational overhead, and Auto Scaling adjusts capacity to demand, optimizing both scalability and cost efficiency.

## 18. Design a cloud architecture in AWS that satisfies scalability, high availability, and fault tolerance requirements

- Bloom: `create`
- Item ID: `5cd52ad9-d7fe-4e45-8ea6-01ddbce3a16a`
- Stem: An architect is designing a system that must continue operating even if one of its components fails. The system should automatically detect and replace failed components. Which design principle should be applied?
- Choices:
- **a** Design for failure by implementing health checks and Auto Scaling to replace unhealthy instances.
- **b** Design for redundancy by using a single instance with frequent backups.
- **c** Design for simplicity by using a monolithic architecture with no redundancy.
- **d** Design for performance by using the largest instance type available.
- Correct choice: **a**
- Explanation: Fault tolerance in AWS is achieved by designing for failure, using health checks and Auto Scaling to automatically replace unhealthy instances, ensuring the system remains operational.

## 19. Design a cloud architecture in AWS that satisfies scalability, high availability, and fault tolerance requirements

- Bloom: `create`
- Item ID: `42ff3df4-888c-4be4-bf15-728c3577b11e`
- Stem: A team is designing a cloud architecture for a critical application that must be highly available and fault tolerant. They need to distribute traffic across multiple instances and ensure that if one instance fails, traffic is routed to healthy instances. Which AWS services should they use?
- Choices:
- **a** Application Load Balancer and Auto Scaling groups across multiple Availability Zones.
- **b** Network Load Balancer and a single EC2 instance.
- **c** Classic Load Balancer and a fixed set of instances in one Availability Zone.
- **d** API Gateway and Lambda functions with no load balancing.
- Correct choice: **a**
- Explanation: Using an Application Load Balancer with Auto Scaling groups across multiple Availability Zones provides high availability and fault tolerance by distributing traffic and replacing unhealthy instances.

## 20. Design a cloud architecture in AWS that satisfies scalability, high availability, and fault tolerance requirements

- Bloom: `create`
- Item ID: `cffae887-fa09-4fa0-8588-8059d8300e6f`
- Stem: An architect is designing a cost-efficient architecture that must handle variable workloads. Which design principle is most important to achieve this?
- Choices:
- **a** Over-provision resources to handle peak load at all times.
- **b** Use Auto Scaling to adjust capacity based on demand.
- **c** Keep all resources running at maximum capacity continuously.
- **d** Use only on-premises servers to avoid cloud costs.
- Correct choice: **b**
- Explanation: Auto Scaling dynamically adjusts capacity to match demand, avoiding over-provisioning and reducing costs.

## 21. Design a cloud architecture in AWS that satisfies scalability, high availability, and fault tolerance requirements

- Bloom: `create`
- Item ID: `adfd3225-e1bb-481f-8b6e-97ecdfa195f8`
- Stem: A company wants to build a cost-efficient architecture that can scale to handle variable workloads. They also need to monitor resource utilization to optimize costs. Which approach should they take?
- Choices:
- **a** Use Auto Scaling to match capacity to demand and CloudWatch to monitor and optimize resource usage.
- **b** Over-provision resources to handle peak demand and use manual monitoring.
- **c** Use reserved instances for all workloads and ignore monitoring.
- **d** Use a single instance with scheduled scaling based on historical data.
- Correct choice: **a**
- Explanation: Auto Scaling adjusts capacity based on demand, and CloudWatch monitoring provides visibility into performance and health, enabling cost efficiency and reliability.

## 22. Design a cloud architecture in AWS that satisfies scalability, high availability, and fault tolerance requirements

- Bloom: `create`
- Item ID: `f3eac817-3296-4908-abfe-39ea1bc8e257`
- Stem: A startup is designing a web application that must handle unpredictable traffic spikes while keeping costs low. The architecture should automatically adjust resource capacity based on demand and continuously track performance and health. Which combination of AWS capabilities should be central to this design?
- Choices:
- **a** Auto Scaling and Amazon CloudWatch
- **b** Manual scaling and periodic log analysis
- **c** Static provisioning and monthly performance reviews
- **d** Reserved instances and annual capacity planning
- Correct choice: **a**
- Explanation: Auto Scaling automatically adjusts capacity based on demand, and Amazon CloudWatch continuously monitors performance and health, ensuring reliability and cost efficiency.

## 23. Design a cloud architecture in AWS that satisfies scalability, high availability, and fault tolerance requirements

- Bloom: `create`
- Item ID: `6155f035-6757-40b0-8cc2-eeac068dfdf5`
- Stem: A startup wants to focus on application development rather than infrastructure management. They need a highly available and scalable architecture. Which design approach should they choose?
- Choices:
- **a** Use managed services like AWS Lambda and API Gateway with Auto Scaling and CloudWatch.
- **b** Manage their own EC2 instances with Auto Scaling and custom monitoring.
- **c** Use a single dedicated server with manual scaling.
- **d** Use a monolithic architecture on a single instance with no redundancy.
- Correct choice: **a**
- Explanation: Managed services reduce operational overhead and support scalability and high availability, while Auto Scaling and CloudWatch ensure performance and health monitoring.

## 24. Design a cloud architecture in AWS that satisfies scalability, high availability, and fault tolerance requirements

- Bloom: `create`
- Item ID: `6810f82f-8cf9-419d-b912-6dc65c1a72e2`
- Stem: A team is designing a highly available application on AWS. They need to continuously monitor the health and performance of their resources to ensure reliability. Which AWS service should they integrate for this purpose?
- Choices:
- **a** Amazon CloudWatch
- **b** Auto Scaling
- **c** A managed database service
- **d** A content delivery network
- Correct choice: **a**
- Explanation: Amazon CloudWatch is the AWS service designed to continuously track performance and health, ensuring reliability.

## 25. Distinguish between IaaS, PaaS, and SaaS service models and cloud-based, hybrid, and on-premises deployment models

- Bloom: `understand`
- Item ID: `7c81c14c-65ed-41df-912d-7039184c2eea`
- Stem: Which of the following is a benefit of cloud computing that allows an organization to increase resources automatically as demand grows?
- Choices:
- **a** Scalability
- **b** Flexibility
- **c** Pay-as-you-go pricing
- **d** IaaS
- Correct choice: **a**
- Explanation: Scalability is the ability to increase or decrease resources as needed, which is a key benefit of cloud computing.

## 26. Distinguish between IaaS, PaaS, and SaaS service models and cloud-based, hybrid, and on-premises deployment models

- Bloom: `understand`
- Item ID: `12169f2f-343f-443f-b2e4-f1fbd3ff373d`
- Stem: Which of the following is a cloud service model?
- Choices:
- **a** IaaS
- **b** Scalability
- **c** Flexibility
- **d** Pay-as-you-go pricing
- Correct choice: **a**
- Explanation: IaaS (Infrastructure as a Service) is one of the three cloud service models, along with PaaS and SaaS.

## 27. Distinguish between IaaS, PaaS, and SaaS service models and cloud-based, hybrid, and on-premises deployment models

- Bloom: `understand`
- Item ID: `42e174d8-a1aa-4ab5-8ec9-9dafd8b37649`
- Stem: Which of the following is NOT one of the three main cloud service models?
- Choices:
- **a** IaaS
- **b** PaaS
- **c** SaaS
- **d** DaaS
- Correct choice: **d**
- Explanation: The three main cloud service models are IaaS, PaaS, and SaaS. DaaS (Desktop as a Service) is not one of the three primary service models.

## 28. Distinguish between IaaS, PaaS, and SaaS service models and cloud-based, hybrid, and on-premises deployment models

- Bloom: `understand`
- Item ID: `c0992900-51d0-4e6d-b1b0-347719e2c5be`
- Stem: Which of the following sets contains only cloud service models?
- Choices:
- **a** IaaS, PaaS, SaaS
- **b** IaaS, PaaS, DaaS
- **c** PaaS, SaaS, CaaS
- **d** IaaS, SaaS, XaaS
- Correct choice: **a**
- Explanation: The three main cloud service models are IaaS (Infrastructure as a Service), PaaS (Platform as a Service), and SaaS (Software as a Service). DaaS, CaaS, and XaaS are not among the three primary service models.

## 29. Distinguish between IaaS, PaaS, and SaaS service models and cloud-based, hybrid, and on-premises deployment models

- Bloom: `understand`
- Item ID: `892c11db-95a3-4999-a552-8d4b3f2bf6fd`
- Stem: What do IaaS, PaaS, and SaaS represent in cloud computing?
- Choices:
- **a** Cloud deployment models
- **b** Cloud service models
- **c** Cloud benefits
- **d** Cloud pricing models
- Correct choice: **b**
- Explanation: IaaS, PaaS, and SaaS are the three main cloud service models, which define the level of abstraction and management provided by the cloud provider.

## 30. Distinguish between IaaS, PaaS, and SaaS service models and cloud-based, hybrid, and on-premises deployment models

- Bloom: `understand`
- Item ID: `d531a950-cac1-45cc-9b7d-fccca6e4762c`
- Stem: Which two categories are used to classify cloud computing offerings?
- Choices:
- **a** Deployment models and service models
- **b** Public and private clouds
- **c** IaaS and PaaS
- **d** Scalability and flexibility
- Correct choice: **a**
- Explanation: Cloud computing offerings are classified by deployment models (where the cloud is hosted) and service models (what is provided). Public/private clouds are types of deployment models, IaaS/PaaS are service models, and scalability/flexibility are benefits.


