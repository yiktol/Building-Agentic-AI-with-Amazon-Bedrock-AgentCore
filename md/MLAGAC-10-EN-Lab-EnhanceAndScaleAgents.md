# Enhance and Scale Agents with Amazon Bedrock AgentCore

> © 2026 Amazon Web Services, Inc. or its affiliates. All rights reserved. This work may not be reproduced or redistributed, in whole or in part, without prior written permission from Amazon Web Services, Inc. Commercial copying, lending, or selling is prohibited. All trademarks are the property of their owners.

> **Note:** Do not include any personal, identifying, or confidential information into the lab environment. Information entered may be visible to others.

Corrections, feedback, or other questions? Contact us at [AWS Training and Certification](https://aws.amazon.com/training/).

---

## Lab overview

You are a Machine Learning Engineer at AnyCompany, a rapidly growing e-commerce platform that serves millions of customers worldwide. Your team has successfully built a basic customer support agent prototype, but now faces the challenge of scaling it to handle enterprise-level demands while maintaining personalized customer experiences. This lab demonstrates the typical journey you'll encounter when transforming agent prototypes into production-ready systems that deliver real business value.

You'll discover how two key Bedrock AgentCore capabilities accelerate this transformation: **AgentCore Memory** and **AgentCore Gateway**. AgentCore Memory enables your AI assistants to maintain persistent conversation context and remember customer preferences across sessions. AgentCore Gateway provides secure, centralized access to Lambda-based tools and functions. The security portion is automatically managed by **AgentCore Identity**, which enables AI agents to securely access AWS resources as well as help deal with inbound user authentication by working with Amazon Cognito. It also enables AI agents to securely access third-party tools and services.

## Objectives

By the end of this lab, you will be able to do the following:

- Implement persistent memory capabilities using AgentCore Memory.
- Build centralized tool infrastructure using AgentCore Gateway with Lambda functions.
- Configure JWT-based authentication for secure gateway access.

## Technical knowledge prerequisites

- Basic understanding of AWS services (Lambda, API Gateway, DynamoDB)
- Intermediate proficiency with Python programming language
- Familiarity with generative AI concepts

## Icon key

Various icons are used throughout this lab to call attention to different types of instructions and notes. The following list explains the purpose for each icon:

- **Caution:** Information of special interest or importance (not so important to cause problems with the equipment or data if you miss it, but it could result in the need to repeat certain steps).
- **Note:** A hint, tip, or important guidance.
- **Task complete:** A conclusion or summary point in the lab.
- **Warning:** An action that is irreversible and could potentially impact the failure of a command or process (including warnings about configurations that cannot be changed after they are made).

---

## Start lab

1. To launch the lab, at the top of the page, choose **Start Lab**.

   > **Caution:** You must wait for the provisioned AWS services to be ready before you can continue.

2. To open the lab, choose **Open Console**.

   You are automatically signed in to the AWS Management Console in a new web browser tab.

   > **Warning:** Do not change the Region unless instructed.

### Common sign-in errors

#### Error: You must first sign out

If you see the message, *You must first log out before logging into a different AWS account*:

1. Choose the **click here** link.
2. Close your Amazon Web Services Sign In web browser tab and return to your initial lab page.
3. Choose **Open Console** again.

#### Error: Choosing Start Lab has no effect

In some cases, certain pop-up or script blocker web browser extensions might prevent the **Start Lab** button from working as intended. If you experience an issue starting the lab:

1. Add the lab domain name to your pop-up or script blocker's allow list or turn it off.
2. Refresh the page and try again.

---

## Lab environment

The following diagram shows the architecture you create in this lab:

> Agent enhanced with AgentCore Memory for persistent customer context, and AgentCore Gateway for secure, centralized tool management.

**Image description:** Agent enhanced with AgentCore Memory for persistent customer context, and AgentCore Gateway for secure, centralized tool management.

> **Note:** The Lambda functions (and the DynamoDB tables they access) are already deployed in your environment, allowing you to focus on implementing AgentCore Memory and Gateway capabilities.

### Services used in this lab

**Amazon Bedrock**
Amazon Bedrock is a fully managed service that provides access to foundation models (FMs) from leading AI companies. It enables developers to build generative AI applications using these models without having to train or deploy them themselves.

**Amazon Bedrock AgentCore**
Amazon Bedrock AgentCore helps you deploy and operate AI agents securely at scale — using any framework and model. It provides you with the capability to move from prototype to production faster.

**Amazon Cognito**
Amazon Cognito lets you add user sign-up, sign-in, and access control to your web and mobile applications within minutes. It is a developer-centric, cost-effective service that provides secure, tenant-based identity stores and federation options that can scale to millions of users. Additionally, Amazon Bedrock AgentCore Identity, powered by Amazon Cognito, enables AI agents to securely access AWS resources or third-party tools and services with robust access controls, while streamlining agent development and user experience.

**AWS Lambda**
AWS Lambda is a serverless compute service that runs code in response to events without requiring server management.

**Amazon DynamoDB**
Amazon DynamoDB is a fully managed NoSQL database service that provides fast and predictable performance with seamless scalability.

### AWS services not used in this lab

AWS service capabilities used in this lab are limited to what the lab requires. Expect errors when accessing other services or performing actions beyond those provided in this lab guide.

---

## Task 1: Open the Code Editor IDE and run the notebook

In this task, you open the Code Editor IDE and run the provided notebook to build an enhanced customer support agent.

1. Copy the **IdeUrl** value that is listed to the left of these instructions.

2. Open a new browser tab and paste the **IdeUrl** into the address bar.

3. Press **Enter**.

   The Code Editor (VS Code) interface opens in your browser.

4. In the **Explorer** panel on the left, open the `notebook.ipynb` file.

5. When prompted to select a kernel, choose **Python 3.12.13 /usr/bin/python3.12**.

6. Follow the instructions in the notebook and run the provided code cells. To run a cell, select within the cell and press **Shift + Enter** or, at the top of the page, choose the run button.

7. After completing all notebook cells, close the notebook and return to these instructions to proceed to Task 2.

> **Task complete:** You have successfully transformed a basic AI agent prototype into a production-ready system using Amazon Bedrock AgentCore Memory for persistent customer context across sessions and AgentCore Gateway for secure, centralized tool sharing.

---

## Task 2: Explore the AgentCore Dashboard, Lambda functions, and DynamoDB tables

In this task, now with your enhanced customer support agent built, you explore the AgentCore dashboard, Lambda functions, and DynamoDB tables. Make sure you have completed all tasks in the Jupyter notebook before proceeding.

### Explore AgentCore Memory

1. On the AWS Management Console, in the search box, search for and choose **Amazon Bedrock AgentCore**.

2. In the left navigation pane, choose **Memory**.

3. Find and select the link containing **CustomerSupportMemory**.

4. In the **Long-term memory strategies** section, notice the two memory strategies. These are the `USER_PREFERENCE` and `SEMANTIC` strategies you configured in the notebook to enable persistent customer context.

5. In the **Observability** section, you can see the operational metrics for memory. These metrics reflect the memory operations from your agent interactions in the notebook.

### Explore AgentCore Identity

6. In the left navigation pane, choose **Identity**.

7. On the Identity page, notice that the **Outbound Auth** section is empty. This is normal, because in this lab, Identity was not used for outbound auth for any third party tools or APIs. In this lab, Identity was only used for inbound auth.

### Explore AgentCore Gateway

8. In the left navigation pane, choose **Gateways**.

9. Select the **customersupport-gw** link.

10. In the **Targets** section, select **LambdaTarget**.

11. Locate the **Lambda ARN** and notice that the value contains `CustomerSupportLambda`. This is the Lambda function you integrated with AgentCore Gateway.

### Explore the Lambda function

12. On the AWS Management Console, in the search box, search for and choose **Lambda**.

13. Select the **CustomerSupportLambda** function.

14. In the **Code source** section, notice the `web_search` and `check_warranty` python files. These are the functions for the customer support tools that are accessed by AgentCore Gateway.

### Explore the DynamoDB tables

15. On the AWS Management Console, in the search box, search for and choose **DynamoDB**.

16. In the left navigation pane, choose **Tables**.

17. Notice there are two tables called **WarrantyTable** and **CustomerProfileTable**. These DynamoDB tables store warranty and customer data.

18. Find and select the table with **WarrantyTable** in its name.

19. Choose **Explore table items** to view the warranty data.

20. Select the sample warranty record with serial number **ABC12345678**. This record contains warranty information including product details, purchase dates, and coverage information. The warranty checking Lambda function queries the WarrantyTable using the serial number to retrieve warranty status and coverage information.

21. Return to the **Tables** list and choose the table with **CustomerProfileTable** in its name.

22. Choose **Explore table items** to view the customer profile data.

23. Choose the customer record with ID **CUST001**. This record contains contact information, purchase history, and customer tier details.

> **Task complete:** You have successfully explored the AgentCore dashboard, Lambda functions, and DynamoDB tables.

---

## Conclusion

You successfully did the following:

- Implemented persistent memory capabilities using AgentCore Memory.
- Built centralized tool infrastructure using AgentCore Gateway with Lambda functions.
- Configured JWT-based authentication for secure gateway access.

## Additional Resources

- For more information about Bedrock AgentCore, see [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html).
- For more information about Bedrock AgentCore Memory, see [AgentCore Memory Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html).
- For more information about Bedrock AgentCore Gateway, see [AgentCore Gateway Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html).
- For more information about Bedrock AgentCore Identity, see [AgentCore Identity Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity.html).
- For more information about Strands Agents, see [Strands Agents Documentation](https://strandsagents.com/).

---

## End lab

Follow these steps to close the console and end your lab.

1. Return to the AWS Management Console.

2. At the upper-right corner of the page, choose **AWSLabsUser**, and then choose **Sign out**.

3. Choose **End Lab** and then confirm that you want to end your lab.

---

For more information about AWS Training and Certification, see <https://aws.amazon.com/training/>.

**Your feedback is welcome and appreciated.**
If you would like to share any feedback, suggestions, or corrections, please provide the details in our AWS Training and Certification Contact Form.
