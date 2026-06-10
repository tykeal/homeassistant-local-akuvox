<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->
<!-- markdownlint-disable MD013 -->

# Feature Specification: Contact & Group Management Services

**Feature Branch**: `006-contact-group-services`
**Created**: 2026-04-24
**Status**: Implemented (retrospective archive)
**Input**: User description: "Add 8 new Home Assistant services for contact and group management on Akuvox devices, leveraging pylocal-akuvox v0.3.0 contact and group CRUD support."

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by
  importance. Each user story/journey must be INDEPENDENTLY TESTABLE - meaning
  if you implement just ONE of them, you should still have a viable MVP
  (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most
  critical. Think of each story as a standalone slice of functionality that
  can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - List Contacts (Priority: P1)

As a home administrator, I want to retrieve all contacts stored on my
Akuvox device so that I can review the current contact directory and use
that information in automations or dashboards.

**Why this priority**: Reading contacts is the foundational operation for
contact management. All other contact operations (create, modify, delete)
build upon the ability to view existing contacts. It provides immediate
value by making previously hidden device data visible within Home Assistant.

**Independent Test**: Can be fully tested by calling the list contacts
service and verifying the returned data matches the contacts configured on
the device. Delivers value as a standalone read-only capability.

**Acceptance Scenarios**:

1. **Given** a configured Akuvox device with existing contacts, **When** the
   user calls the list contacts service, **Then** all contacts are returned
   with their names, IDs, phone numbers, and group assignments.
2. **Given** a configured Akuvox device with no contacts, **When** the user
   calls the list contacts service, **Then** an empty list is returned with
   no errors.
3. **Given** a device with more contacts than fit on one page, **When** the
   user calls the list contacts service with a page number, **Then** only
   the requested page of results is returned.
4. **Given** a device that is unreachable, **When** the user calls the list
   contacts service, **Then** an appropriate error is raised indicating the
   device is unavailable.

---

### User Story 2 - List Groups (Priority: P1)

As a home administrator, I want to retrieve all contact groups defined on
my Akuvox device so that I can see the available groupings and reference
them when creating or modifying contacts.

**Why this priority**: Reading groups is a foundational operation on par with
listing contacts. Groups are referenced when assigning contacts to groups,
so visibility into existing groups is a prerequisite for meaningful contact
management.

**Independent Test**: Can be fully tested by calling the list groups service
and verifying the returned data matches the groups configured on the device.

**Acceptance Scenarios**:

1. **Given** a configured Akuvox device with existing groups, **When** the
   user calls the list groups service, **Then** all groups are returned with
   their names and IDs.
2. **Given** a configured Akuvox device with no groups, **When** the user
   calls the list groups service, **Then** an empty list is returned with
   no errors.
3. **Given** a device with more groups than fit on one page, **When** the
   user calls the list groups service with a page number, **Then** only the
   requested page of results is returned.
4. **Given** a device that is unreachable, **When** the user calls the list
   groups service, **Then** an appropriate error is raised indicating the
   device is unavailable.

---

### User Story 3 - Add Contact (Priority: P2)

As a home administrator, I want to create a new contact on my Akuvox device
so that I can build and maintain the device's contact directory through
Home Assistant automations.

**Why this priority**: Creating contacts is the first write operation and
enables building the device's contact directory. Contacts can optionally
reference groups, but a group assignment is not required, making this
independently useful.

**Independent Test**: Can be fully tested by creating a contact with valid
parameters and then listing contacts to confirm it appears on the device.

**Acceptance Scenarios**:

1. **Given** a configured Akuvox device, **When** the user calls the add
   contact service with a name, **Then** the contact is created on the
   device and a success response is returned.
2. **Given** a configured Akuvox device, **When** the user calls the add
   contact service with a name, phone number, and group, **Then** the
   contact is created with all specified attributes.
3. **Given** a configured Akuvox device, **When** the user calls the add
   contact service without a name, **Then** a validation error is raised
   indicating that name is required.

---

### User Story 4 - Add Group (Priority: P2)

As a home administrator, I want to create a new contact group on my Akuvox
device so that I can organise contacts into logical groupings for easier
management.

**Why this priority**: Creating groups enables the organisational structure
for contacts. While contacts do not require a group, groups provide value
for managing larger contact directories.

**Independent Test**: Can be fully tested by creating a group with a valid
name and then listing groups to confirm it appears on the device.

**Acceptance Scenarios**:

1. **Given** a configured Akuvox device, **When** the user calls the add
   group service with a name, **Then** the group is created on the device.
2. **Given** a configured Akuvox device, **When** the user calls the add
   group service without a name, **Then** a validation error is raised
   indicating that name is required.

---

### User Story 5 - Modify Contact (Priority: P2)

As a home administrator, I want to modify an existing contact on my Akuvox
device so that I can update contact details without recreating the entire
contact entry.

**Why this priority**: Modifying contacts completes the contact write
operations and avoids forcing users to delete and recreate contacts for
minor changes such as updating a phone number or group assignment.

**Independent Test**: Can be fully tested by modifying a contact attribute
and then listing contacts to confirm the change persists on the device.

**Acceptance Scenarios**:

1. **Given** a device with an existing contact, **When** the user calls the
   modify contact service with the contact ID and updated fields, **Then**
   only the specified fields are updated and all other fields remain
   unchanged.
2. **Given** a device with an existing contact, **When** the user calls the
   modify contact service with a non-existent contact ID, **Then** an
   appropriate error is raised indicating the contact was not found.
3. **Given** a device with an existing contact, **When** the user calls the
   modify contact service without providing the contact ID, **Then** a
   validation error is raised indicating that the ID is required.

---

### User Story 6 - Modify Group (Priority: P2)

As a home administrator, I want to modify an existing group on my Akuvox
device so that I can rename groups without recreating them.

**Why this priority**: Modifying groups completes the group write operations
and supports ongoing organisational maintenance.

**Independent Test**: Can be fully tested by modifying a group name and then
listing groups to confirm the change persists on the device.

**Acceptance Scenarios**:

1. **Given** a device with an existing group, **When** the user calls the
   modify group service with the group ID and a new name, **Then** the
   group name is updated on the device.
2. **Given** a device, **When** the user calls the modify group service with
   a non-existent group ID, **Then** an appropriate error is raised
   indicating the group was not found.
3. **Given** a device with an existing group, **When** the user calls the
   modify group service without a name, **Then** a validation error is
   raised indicating that name is required.

---

### User Story 7 - Delete Contact (Priority: P3)

As a home administrator, I want to delete one or more contacts from my
Akuvox device so that I can remove outdated or unnecessary entries from the
contact directory.

**Why this priority**: Deletion completes the full CRUD lifecycle for
contacts. Batch deletion support adds efficiency for bulk cleanup operations.

**Independent Test**: Can be fully tested by deleting a contact by ID and
then listing contacts to confirm it is no longer present.

**Acceptance Scenarios**:

1. **Given** a device with an existing contact, **When** the user calls the
   delete contact service with the contact ID, **Then** the contact is
   removed from the device.
2. **Given** a device with multiple existing contacts, **When** the user
   calls the delete contact service with a list of contact IDs, **Then**
   all specified contacts are removed from the device in a single operation.
3. **Given** a device, **When** the user calls the delete contact service
   with a non-existent contact ID, **Then** an appropriate error is raised
   indicating the contact was not found.

---

### User Story 8 - Delete Group (Priority: P3)

As a home administrator, I want to delete a group from my Akuvox device so
that I can remove unused or obsolete groupings from the contact directory.

**Why this priority**: Deletion completes the full CRUD lifecycle for groups
and is essential for ongoing directory maintenance.

**Independent Test**: Can be fully tested by deleting a group by ID and then
listing groups to confirm it is no longer present.

**Acceptance Scenarios**:

1. **Given** a device with an existing group, **When** the user calls the
   delete group service with the group ID, **Then** the group is removed
   from the device.
2. **Given** a device, **When** the user calls the delete group service with
   a non-existent group ID, **Then** an appropriate error is raised
   indicating the group was not found.

---

### Edge Cases

- What happens when the device returns a partial or malformed response during
  contact or group listing? The system should handle parsing failures
  gracefully and return an error rather than partial data.
- What happens when a user attempts to create a contact or group while the
  device is in the middle of a firmware update or restart? The system should
  detect the connection failure and report the device as unavailable.
- What happens when the user provides a page number that exceeds the total
  number of pages? The system should return an empty list.
- What happens when multiple Home Assistant users call write services
  (create, modify, delete) simultaneously targeting the same device? The
  device API does not support optimistic concurrency. Callers should
  serialise operations targeting the same device. The integration documents
  this limitation but does not enforce serialisation.
- What happens when a group is deleted while contacts still reference it?
  The system should allow the deletion (this is device-managed behaviour)
  but log a warning about orphaned contact-group assignments.
- What happens when service parameters contain special characters or
  excessively long values? The system should validate input lengths and
  character sets before sending to the device.
- What happens when batch contact deletion includes a mix of valid and
  invalid IDs? The behaviour is determined by the underlying library; the
  integration should propagate any errors raised by the device.
- What happens when a contact is created with a group value that does not
  correspond to an existing group on the device? The system should pass the
  value through to the device and let the device determine the outcome.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expose a service to list all contacts from the
  device, returning contact details including name, ID, phone number, and
  group assignment.
- **FR-002**: System MUST expose a service to create a new contact on the
  device, accepting a required name and optional phone number and group
  parameters.
- **FR-003**: System MUST expose a service to modify an existing contact on
  the device, identified by contact ID, allowing partial updates to name,
  phone number, and group.
- **FR-004**: System MUST expose a service to delete one or more contacts
  from the device, accepting either a single contact ID or a list of
  contact IDs for batch deletion.
- **FR-005**: System MUST expose a service to list all groups from the
  device, returning group details including name and ID.
- **FR-006**: System MUST expose a service to create a new group on the
  device, accepting a required group name.
- **FR-007**: System MUST expose a service to modify an existing group on
  the device, identified by group ID, requiring a new group name.
- **FR-008**: System MUST expose a service to delete a group from the
  device, identified by group ID.
- **FR-009**: System MUST validate all service input parameters before
  communicating with the device, rejecting invalid values with descriptive
  error messages.
- **FR-010**: System MUST support optional pagination for list operations
  (contacts and groups), allowing the caller to request a specific page of
  results.
- **FR-011**: System MUST propagate device communication errors (connection
  failures, authentication failures, device errors) as appropriate service
  call errors.
- **FR-012**: System MUST scope all services to a specific device entry,
  ensuring multi-device setups route requests to the correct device.
  Services target lock entities, consistent with existing service patterns.
- **FR-013**: System MUST fire a `local_akuvox_contact_changed` event on the
  Home Assistant event bus after successful contact write operations (create,
  modify, delete) to enable automations that react to contact directory
  changes.
- **FR-014**: System MUST fire a `local_akuvox_group_changed` event on the
  Home Assistant event bus after successful group write operations (create,
  modify, delete) to enable automations that react to group changes.
- **FR-015**: System MUST require pylocal-akuvox version 0.3.0 or later as
  a dependency to access the contact and group management API surface.

### Key Entities

- **Contact**: A directory entry on the Akuvox device representing a person
  or endpoint. Key attributes: device-assigned ID, name (required), phone
  number (optional), and group assignment (optional). Contacts are the
  primary records in the device's contact directory.
- **Group**: An organisational category for contacts on the Akuvox device.
  Key attributes: device-assigned ID and name (required). Groups provide a
  way to logically categorise contacts for easier management.

### Assumptions

- The Akuvox device manages all data persistence. The integration acts as a
  pass-through to the device's local API and does not cache or store contact
  or group data within Home Assistant.
- The underlying pylocal-akuvox library (v0.3.0+) handles the HTTP
  communication protocol, serialisation, and deserialisation of contact and
  group data. The integration delegates all device communication to the
  library.
- Services follow the same patterns established by the schedule and user
  management services in feature 003, including entity targeting, error
  handling, and event bus integration.
- Services target lock entities, consistent with the existing service
  registration pattern used by schedule and user services.
- Contact and group IDs are device-assigned string values. The integration
  does not generate or manage these identifiers.
- The device handles referential integrity between contacts and groups. If a
  group is deleted while contacts reference it, the device determines the
  resulting behaviour.
- Event names follow the `local_akuvox_` prefix convention established by
  existing services.
- Batch deletion for contacts passes a list of IDs to the underlying library
  method, which handles the batch operation. The integration does not
  implement its own batching logic.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Administrators can list all contacts and groups from the
  device within 5 seconds of calling the respective service.
- **SC-002**: Administrators can create, modify, and delete contacts and
  groups through service calls with 100% of valid inputs succeeding on the
  first attempt.
- **SC-003**: 100% of invalid inputs (missing required fields, malformed
  IDs) are rejected with a descriptive error message before any device
  communication occurs.
- **SC-004**: All eight services (list/add/modify/delete for both contacts
  and groups) are individually callable from Home Assistant automations,
  scripts, and the developer tools service panel.
- **SC-005**: Contact write operations (create, modify, delete) fire
  `local_akuvox_contact_changed` events and group write operations fire
  `local_akuvox_group_changed` events that automations can trigger on.
- **SC-006**: Service calls against an unreachable device return a clear
  error within 10 seconds rather than hanging indefinitely.
- **SC-007**: Batch contact deletion successfully removes all specified
  contacts in a single service call.
