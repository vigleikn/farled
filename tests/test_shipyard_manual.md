# Manual Testing Guide for Shipyard Integration

## Overview

This guide provides step-by-step instructions for manually testing the shipyard integration feature. Run these tests after the automated test suite passes to verify the user experience.

## Prerequisites

- Application running locally (`python app.py` or via deployment)
- Browser developer console open for checking errors
- No JavaScript errors should appear during any test

---

## Test Scenarios

### 1. Basic Search Functionality

**Objective:** Verify shipyards appear in search results

1. Open the application in your browser
2. Click on the "Fra" (From) input field
3. Type "Fosen" into the input field
4. Wait for the dropdown to appear
5. **Expected Results:**
   - [ ] Dropdown appears below the input
   - [ ] A "Verft" (Shipyard) section appears in the dropdown
   - [ ] "Verft" section appears between "Kaier" (Quays) and "Steder" (Places)
   - [ ] "Fosen Yards AS" is visible in the Verft section
   - [ ] "Rissa" appears as subtitle/city for the shipyard
   - [ ] No JavaScript errors in console

---

### 2. Search Behavior Testing

**Objective:** Verify search works with different input patterns

#### Test 2a: Partial Name Matching
1. Type "Bergen" in the FROM field
2. **Expected Results:**
   - [ ] Shipyards containing "Bergen" appear in Verft section (if any exist)
   - [ ] Kaier (quays) section also shows results for "Bergen"
   - [ ] Results load within 200ms

#### Test 2b: Case Insensitivity
1. Clear the input field
2. Type "FOSEN" (all uppercase)
3. **Expected Results:**
   - [ ] "Fosen Yards AS" still appears in results
   - [ ] Search is case-insensitive (no errors)

#### Test 2c: No Matches
1. Clear the input field
2. Type "NonexistentShipyard999"
3. **Expected Results:**
   - [ ] Verft section does NOT appear if no shipyards match
   - [ ] Other result categories may still appear (if matching)
   - [ ] No errors displayed

#### Test 2d: Generic Search
1. Clear and type "verft" (Norwegian for shipyard)
2. **Expected Results:**
   - [ ] Multiple shipyards appear
   - [ ] Results include many shipyard names containing "verft"
   - [ ] Dropdown remains responsive

---

### 3. Dropdown Positioning and Order

**Objective:** Verify dropdown categories are displayed in correct order

1. Type a search term that returns results in all categories (e.g., "as")
2. **Expected Results:**
   - [ ] Results appear in this exact order:
     1. Kaier (Quays)
     2. Verft (Shipyards)
     3. Steder (Places)
     4. Adresser (Addresses)
   - [ ] Section headers are clearly visible and labeled
   - [ ] Maximum 10 items per category (if available)
   - [ ] Scrolling works if categories are tall

---

### 4. Selecting a Shipyard

**Objective:** Verify shipyard selection works correctly

1. Type "Fosen" in the FROM field
2. Click on "Fosen Yards AS" in the dropdown
3. **Expected Results:**
   - [ ] Dropdown closes automatically
   - [ ] "Fosen Yards AS" appears in the FROM field
   - [ ] "Rissa" (city) appears as a subtitle
   - [ ] A map pin/marker appears on the map at the shipyard location
   - [ ] A blue dot appears on the map indicating the selected point
   - [ ] The map viewport may adjust to show the point
   - [ ] No "kjøre seg fast" (stuck) UI state

---

### 5. Clear Button Functionality

**Objective:** Verify shipyard selection can be cleared

1. With "Fosen Yards AS" selected in FROM field
2. **Expected Results:**
   - [ ] A "clear" button (❌ or ✕) appears next to the shipyard name
   - [ ] Click the clear button
   - [ ] FROM field becomes empty
   - [ ] Map marker disappears
   - [ ] Clear button is no longer visible

---

### 6. Route Calculation with Shipyard

**Objective:** Verify route calculation works with shipyard as start/end point

#### Test 6a: Shipyard as FROM point
1. Select "Fosen Yards AS" in the FROM field
2. Select a quay (e.g., "Harstad") in the TO field
3. Click the "Beregn sjøvei" (Calculate Route) button
4. **Expected Results:**
   - [ ] Route calculation completes successfully
   - [ ] Route appears on the map from Fosen to Harstad
   - [ ] Distance is displayed in nautical miles and km
   - [ ] Route waypoints are shown on the map

#### Test 6b: Shipyard as TO point
1. Select a quay in the FROM field
2. Select a shipyard in the TO field
3. Click "Beregn sjøvei"
4. **Expected Results:**
   - [ ] Route calculation works with shipyard as destination
   - [ ] Route displays correctly on map

---

### 7. Enhanced Callouts - Shipyard Popup Information

**Objective:** Verify shipyard popups show facility information

1. Select any shipyard in the FROM field (e.g., "Fosen Yards AS")
2. Look at the map marker that appears
3. Click on the shipyard marker on the map
4. **Expected Results:**
   - [ ] A popup appears with shipyard information
   - [ ] Popup shows: **Name**, **Address**, **City**, **Postal Code**
   - [ ] Popup shows **Homepage** link (if available in data)
   - [ ] Popup shows **Facilities** section with:
     - [ ] Tørrdokk (Dry dock)
     - [ ] Våtdokk (Wet dock)
     - [ ] Kran (Crane)
     - [ ] Hall information
   - [ ] Homepage link opens in a new tab when clicked
   - [ ] Facility labels are in Norwegian (e.g., "Tørrdokk", not "DocksDry")
   - [ ] Empty facilities don't show in popup (no empty fields)

---

### 8. UI State Management

**Objective:** Verify UI remains in consistent state

1. Select a shipyard
2. Click on the shipyard in dropdown to select it again
3. **Expected Results:**
   - [ ] No duplicate entries in field
   - [ ] No visual glitches
   - [ ] Clear button appears correctly

4. Try selecting FROM, then TO, then FROM again
5. **Expected Results:**
   - [ ] UI state remains consistent
   - [ ] No field values get confused or swapped
   - [ ] Both fields can have different values (one shipyard, one quay)

---

### 9. Mobile/Responsive Testing (if applicable)

**Objective:** Verify shipyard feature works on smaller screens

1. Open application on mobile device or use browser dev tools (responsive mode)
2. Type "Fosen" in search field
3. **Expected Results:**
   - [ ] Dropdown appears and is readable on mobile
   - [ ] Tap to select works (no click issues)
   - [ ] Markers are visible and clickable on mobile
   - [ ] Popups display properly on mobile
   - [ ] No horizontal scrolling issues

---

### 10. Error Handling

**Objective:** Verify graceful error handling

1. Check browser console for any JavaScript errors
2. Try various edge cases:
   - [ ] Very long search strings (50+ characters)
   - [ ] Special characters: éàêëøå
   - [ ] Numbers: "123"
   - [ ] Empty input then backspace
3. **Expected Results:**
   - [ ] No JavaScript errors in console
   - [ ] No console warnings about missing data
   - [ ] Application remains responsive
   - [ ] Clear error messages if something fails

---

## Integration Checklist

### Search & Dropdown
- [ ] Shipyards appear in dropdown results
- [ ] Search is case-insensitive
- [ ] Results load within 200ms
- [ ] Dropdown categories are in correct order
- [ ] Section headers are visible

### Selection & Mapping
- [ ] Clicking shipyard selects it
- [ ] Map marker appears at correct location
- [ ] Clear button works and removes selection
- [ ] UI doesn't enter stuck state

### Route Calculation
- [ ] Routes calculate with shipyard as FROM
- [ ] Routes calculate with shipyard as TO
- [ ] Distance calculations are correct
- [ ] Waypoints display properly

### Callout Information
- [ ] Popups show shipyard details
- [ ] Homepage links are clickable and open in new tab
- [ ] Facilities are labeled in Norwegian
- [ ] Empty facilities are not shown
- [ ] Facility information is organized and readable

### Data Quality
- [ ] All shipyards have valid coordinates (in Norway)
- [ ] All shipyards have names and cities
- [ ] All shipyards have postal codes
- [ ] Coordinates are properly geocoded

---

## Test Results

Date: _______________
Tester: ______________
Browser: ________________
OS: ____________________

### Summary
- [ ] All tests passed
- [ ] Some tests failed (list below)
- [ ] Tests blocked by issues (list below)

### Issues Found

| # | Test Case | Issue | Severity | Notes |
|---|-----------|-------|----------|-------|
| 1 |           |       |          |       |
| 2 |           |       |          |       |
| 3 |           |       |          |       |

### Sign-off

- [ ] Ready for production
- [ ] Needs fixes before production
- [ ] Blocked - needs investigation

Signature: _________________ Date: _________

