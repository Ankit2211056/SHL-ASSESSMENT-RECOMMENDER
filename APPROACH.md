# SHL Assessment Consultant Agent – Approach Document

## 1. Problem Understanding

The objective was to build a conversational SHL Assessment Recommender that can:

* Understand hiring requirements through natural language conversations.
* Ask clarifying questions when information is incomplete.
* Recommend relevant SHL assessments based on role, seniority, skills, and behavioral requirements.
* Refine recommendations when requirements change.
* Compare assessments using catalog information.
* Return structured API responses through the required endpoints.

The solution was implemented as a FastAPI-based conversational service with a stateless architecture and LLM-assisted reasoning.

---

## 2. System Design

### Backend Architecture

The application uses a stateless FastAPI backend.

The client sends the complete conversation history with each request. This eliminates the need for server-side session storage and simplifies deployment and scaling.

The backend performs the following steps:

1. Receive conversation history.
2. Extract hiring intent and relevant role information.
3. Identify missing information and generate clarification questions when required.
4. Match requirements against the SHL assessment catalog.
5. Generate recommendations or comparisons.
6. Return a structured JSON response.

### API Endpoints

The solution exposes the required endpoints:

* `GET /health`
* `POST /chat`

Additional utility endpoints are available for development and catalog inspection.

---

## 3. Catalog Grounding Strategy

A structured SHL assessment catalog is maintained locally within the application.

Each catalog entry contains information such as:

* Assessment name
* Assessment type
* Description
* Relevant skills
* Target job levels
* Official SHL URL

The recommendation engine only returns assessments that exist in the catalog.

This approach helps prevent hallucinated assessment names, invalid URLs, and unsupported recommendations.

---

## 4. Conversational Recommendation Logic

The recommendation workflow follows three stages:

### Clarification Stage

When the user's request lacks sufficient information, the assistant asks follow-up questions.

Examples:

* Job role not specified
* Seniority level missing
* Technical vs behavioral requirements unclear

### Recommendation Stage

Once enough information is available, the assistant recommends assessments that best align with:

* Technical skills
* Cognitive requirements
* Leadership requirements
* Behavioral competencies
* Job level

### Comparison Stage

When the user requests a comparison, the assistant retrieves information from the catalog and generates a side-by-side explanation of the selected assessments.

---

## 5. Prompt Design

The prompt was designed to guide the model toward:

* Asking clarification questions when necessary.
* Remaining focused on SHL assessment consulting.
* Producing grounded recommendations.
* Avoiding unsupported claims.
* Returning structured responses.

The model is instructed to recommend only catalog-supported assessments and to use catalog evidence when generating comparisons.

---

## 6. Evaluation Approach

Evaluation was performed using the provided example conversations and additional manually created test scenarios.

The following aspects were validated:

### Recommendation Relevance

Recommendations were reviewed to ensure they matched:

* Role requirements
* Seniority level
* Technical competencies
* Behavioral requirements

### Catalog Grounding

All recommended assessments were verified against the local SHL catalog to ensure:

* Valid assessment names
* Valid SHL URLs
* Consistent metadata

### Conversation Quality

Testing verified that the assistant:

* Asked clarification questions when appropriate.
* Refined recommendations when requirements changed.
* Supported assessment comparison requests.

### Schema Validation

Responses were validated against the API response structure to ensure consistent JSON output.

---

## 7. Challenges and Improvements

### Challenge 1: Incomplete User Requirements

Many conversations begin with limited information.

Solution:

The assistant was designed to identify missing information and ask targeted clarification questions before generating recommendations.

### Challenge 2: Recommendation Grounding

Direct language-model generation can sometimes introduce unsupported assessment names.

Solution:

Recommendations are restricted to entries available in the local SHL catalog.

### Challenge 3: Consistent API Responses

Maintaining a predictable response structure is important for frontend integration and automated evaluation.

Solution:

Structured response models were used to enforce consistent output formatting.

---

## 8. Development Process

The project was developed using an iterative workflow involving:

* FastAPI backend development
* Catalog structuring and validation
* Prompt refinement
* Manual conversation testing
* API validation through Swagger UI and local endpoint testing

AI-assisted development tools were used for code scaffolding, debugging assistance, and implementation support throughout the development process.

---

## 9. Conclusion

The final solution provides a conversational SHL assessment recommendation system capable of asking clarifying questions, generating grounded recommendations, refining suggestions based on changing requirements, and comparing assessments using catalog information. The system is lightweight, stateless, deployable, and aligned with the assignment requirements.
