# API Integration Requirements Document: Customer Profile API

_Generated automatically by the API Requirements Documentation Kit on 2026-09-21 21:52 UTC from `examples/customer_profile_api.yaml`. Sections marked `[BA TO COMPLETE: business meaning of this field]` require Business Analyst review before this document is finalized._

## 1. API Overview
- **API Title:** Customer Profile API
- **API Version:** 1.2.0
- **Number of Endpoints Documented:** 3

A fictional, synthetic API used to manage core customer profile records for demonstration purposes. This specification and all data within it are entirely made up and do not represent any real system, company, or dataset. It exists solely to demonstrate how a Business Analyst can turn a machine-readable OpenAPI specification into a human-readable API integration requirements document.

## 2. Endpoint Summary
| # | Method | Path | Summary |
|---|---|---|---|
| 1 | POST | `/customers` | Create a new customer profile |
| 2 | GET | `/customers/{id}` | Retrieve a single customer profile |
| 3 | PATCH | `/customers/{id}` | Update selected fields on an existing customer profile |

## 3. Endpoint Requirements
### 1. POST `/customers`

_Operation ID: `createCustomer`_

#### Business Purpose
Creates a new customer profile record. Typically invoked by an onboarding workflow the first time a new customer is registered with the business, for example after a new account application is approved.

#### Request Data Mapping
_Required in every request._

| Field | Type | Required? | Business Meaning |
|---|---|---|---|
| firstName | string | Yes | The customer's legal first name. |
| lastName | string | Yes | The customer's legal last name. |
| emailAddress | string (email) | Yes | The customer's primary email address used for account communications. |
| phoneNumber | string | No | The customer's primary contact phone number, in E.164 format. |
| dateOfBirth | string (date) | No | The customer's date of birth, used for identity verification. |
| preferredContactMethod | string, one of: EMAIL, PHONE, MAIL | No | The channel the customer has indicated they prefer to be contacted through. |
| externalReferenceNumber | string | No | A business-assigned reference number used to correlate this profile with records in other internal systems. |

#### Response Data Mapping
_Primary success response: `201` - The customer profile was created successfully and is returned in the response body._

| Field | Type | Required? | Business Meaning |
|---|---|---|---|
| id | string (uuid) | Yes | The unique identifier assigned to the customer profile. |
| firstName | string | Yes | The customer's legal first name. |
| lastName | string | Yes | The customer's legal last name. |
| emailAddress | string (email) | Yes | The customer's primary email address used for account communications. |
| phoneNumber | string | No | The customer's primary contact phone number, in E.164 format. |
| dateOfBirth | string (date) | No | The customer's date of birth, used for identity verification. |
| preferredContactMethod | string, one of: EMAIL, PHONE, MAIL | No | The channel the customer has indicated they prefer to be contacted through. |
| status | string, one of: ACTIVE, ARCHIVED, PENDING_VERIFICATION | Yes | The current lifecycle status of the customer profile. |
| externalReferenceNumber | string | No | A business-assigned reference number used to correlate this profile with records in other internal systems. |
| createdAt | string (date-time) | Yes | The timestamp at which the profile was originally created. |
| updatedAt | string (date-time) | No | The timestamp at which the profile was last modified. |

#### Business Rules
[BA TO COMPLETE: describe any business rule, validation, or downstream effect associated with this operation, e.g. approval thresholds, notification triggers, or data retention requirements.]

#### Error Scenarios
| Status Code | Meaning | When It Occurs (per spec) | Business Handling |
|---|---|---|---|
| 400 | Bad Request - Client/Validation Error | The request body failed validation, such as a missing required field or an invalid date of birth format. | [BA TO COMPLETE: describe how the business expects this scenario to be handled, e.g. user-facing message, retry policy, or escalation.] |
| 409 | Conflict | A customer profile already exists with the same unique business identifier (for example, the same email address or external reference number). | [BA TO COMPLETE: describe how the business expects this scenario to be handled, e.g. user-facing message, retry policy, or escalation.] |
| 500 | Internal Server Error | An unexpected internal error occurred while creating the customer profile. | [BA TO COMPLETE: describe how the business expects this scenario to be handled, e.g. user-facing message, retry policy, or escalation.] |


### 2. GET `/customers/{id}`

_Operation ID: `getCustomerById`_

#### Business Purpose
Returns the current profile record for a single customer, identified by their unique customer identifier. Used by downstream systems that need to display or verify a customer's core profile details, such as a self-service portal or an agent-facing servicing screen.

**Parameters**

| Parameter | Location | Type | Required? | Business Meaning |
|---|---|---|---|---|
| id | path | string | Yes | The unique identifier assigned to the customer profile. |
| includeArchived | query | boolean | No | When true, allows retrieval of a customer profile that has been archived (soft-deleted). Defaults to false. |

#### Request Data Mapping
_This operation does not take a request body._

#### Response Data Mapping
_Primary success response: `200` - The customer profile was found and is returned in the response body._

| Field | Type | Required? | Business Meaning |
|---|---|---|---|
| id | string (uuid) | Yes | The unique identifier assigned to the customer profile. |
| firstName | string | Yes | The customer's legal first name. |
| lastName | string | Yes | The customer's legal last name. |
| emailAddress | string (email) | Yes | The customer's primary email address used for account communications. |
| phoneNumber | string | No | The customer's primary contact phone number, in E.164 format. |
| dateOfBirth | string (date) | No | The customer's date of birth, used for identity verification. |
| preferredContactMethod | string, one of: EMAIL, PHONE, MAIL | No | The channel the customer has indicated they prefer to be contacted through. |
| status | string, one of: ACTIVE, ARCHIVED, PENDING_VERIFICATION | Yes | The current lifecycle status of the customer profile. |
| externalReferenceNumber | string | No | A business-assigned reference number used to correlate this profile with records in other internal systems. |
| createdAt | string (date-time) | Yes | The timestamp at which the profile was originally created. |
| updatedAt | string (date-time) | No | The timestamp at which the profile was last modified. |

#### Business Rules
[BA TO COMPLETE: describe any business rule, validation, or downstream effect associated with this operation, e.g. approval thresholds, notification triggers, or data retention requirements.]

#### Error Scenarios
| Status Code | Meaning | When It Occurs (per spec) | Business Handling |
|---|---|---|---|
| 400 | Bad Request - Client/Validation Error | The request was malformed, such as an invalid identifier format that does not match the expected UUID pattern. | [BA TO COMPLETE: describe how the business expects this scenario to be handled, e.g. user-facing message, retry policy, or escalation.] |
| 404 | Not Found | No customer profile exists for the supplied identifier. | [BA TO COMPLETE: describe how the business expects this scenario to be handled, e.g. user-facing message, retry policy, or escalation.] |
| 500 | Internal Server Error | An unexpected internal error occurred while retrieving the customer profile. | [BA TO COMPLETE: describe how the business expects this scenario to be handled, e.g. user-facing message, retry policy, or escalation.] |


### 3. PATCH `/customers/{id}`

_Operation ID: `updateCustomerById`_

#### Business Purpose
Applies a partial update to an existing customer profile. Only the fields supplied in the request body are changed; all other existing field values are left untouched. Typically used when a customer updates their contact details or preferences through a self-service channel.

**Parameters**

| Parameter | Location | Type | Required? | Business Meaning |
|---|---|---|---|---|
| id | path | string | Yes | The unique identifier assigned to the customer profile to update. |

#### Request Data Mapping
_Required in every request._

| Field | Type | Required? | Business Meaning |
|---|---|---|---|
| emailAddress | string (email) | No | The customer's primary email address used for account communications. |
| phoneNumber | string | No | The customer's primary contact phone number, in E.164 format. |
| preferredContactMethod | string, one of: EMAIL, PHONE, MAIL | No | The channel the customer has indicated they prefer to be contacted through. |
| status | string, one of: ACTIVE, ARCHIVED, PENDING_VERIFICATION | No | The current lifecycle status of the customer profile. |

#### Response Data Mapping
_Primary success response: `200` - The customer profile was updated successfully and is returned in the response body._

| Field | Type | Required? | Business Meaning |
|---|---|---|---|
| id | string (uuid) | Yes | The unique identifier assigned to the customer profile. |
| firstName | string | Yes | The customer's legal first name. |
| lastName | string | Yes | The customer's legal last name. |
| emailAddress | string (email) | Yes | The customer's primary email address used for account communications. |
| phoneNumber | string | No | The customer's primary contact phone number, in E.164 format. |
| dateOfBirth | string (date) | No | The customer's date of birth, used for identity verification. |
| preferredContactMethod | string, one of: EMAIL, PHONE, MAIL | No | The channel the customer has indicated they prefer to be contacted through. |
| status | string, one of: ACTIVE, ARCHIVED, PENDING_VERIFICATION | Yes | The current lifecycle status of the customer profile. |
| externalReferenceNumber | string | No | A business-assigned reference number used to correlate this profile with records in other internal systems. |
| createdAt | string (date-time) | Yes | The timestamp at which the profile was originally created. |
| updatedAt | string (date-time) | No | The timestamp at which the profile was last modified. |

#### Business Rules
[BA TO COMPLETE: describe any business rule, validation, or downstream effect associated with this operation, e.g. approval thresholds, notification triggers, or data retention requirements.]

#### Error Scenarios
| Status Code | Meaning | When It Occurs (per spec) | Business Handling |
|---|---|---|---|
| 400 | Bad Request - Client/Validation Error | The request body failed validation, such as an invalid email address format or an unsupported preferred contact method. | [BA TO COMPLETE: describe how the business expects this scenario to be handled, e.g. user-facing message, retry policy, or escalation.] |
| 404 | Not Found | No customer profile exists for the supplied identifier. | [BA TO COMPLETE: describe how the business expects this scenario to be handled, e.g. user-facing message, retry policy, or escalation.] |
| 409 | Conflict | The update could not be applied because the profile was modified by another process since it was last read (an optimistic concurrency conflict). | [BA TO COMPLETE: describe how the business expects this scenario to be handled, e.g. user-facing message, retry policy, or escalation.] |
| 500 | Internal Server Error | An unexpected internal error occurred while updating the customer profile. | [BA TO COMPLETE: describe how the business expects this scenario to be handled, e.g. user-facing message, retry policy, or escalation.] |


---
_This document was generated from an OpenAPI specification and is intended as a starting point for a Business Analyst, not a finished deliverable. Every placeholder above must be reviewed and completed before this document is shared with a development team._
