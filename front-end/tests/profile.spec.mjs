import {test, expect} from "@playwright/test";
import {TIMELINE_USERNAMES_ELEMENTS_LOCATOR, loginAsSample, loginAsJustSomeGuy, waitForLocatorToHaveMatches} from "./test-utils.mjs";

test.describe("Profile View", () => {
  test("shows own profile when logged in", async ({page}) => {
    // Given a profile view
    // When I am logged in as sample
    await loginAsSample(page);
    await page.goto("/#/profile/sample");

    // Then I see logout button, profile, and timeline of my posts only
    await expect(
      page.locator("#logout-container [data-logout-button]")
    ).toBeVisible();
    await expect(
      page.locator("#profile-container header a[data-username]")
    ).toBeVisible();

    await waitForLocatorToHaveMatches(page, TIMELINE_USERNAMES_ELEMENTS_LOCATOR);
    const postUsernames = new Set(await page.locator(TIMELINE_USERNAMES_ELEMENTS_LOCATOR).allInnerTexts());
    expect(postUsernames).toEqual(new Set(["sample"]));

    // And bloom form is not attached
    await expect(
      page.locator("#bloom-form-container [data-form]")
    ).not.toBeAttached();
  });

  test("shows other user's profile with follow button", async ({page}) => {
    // Given I am logged in as AS
    await loginAsJustSomeGuy(page);
    // When I go to sample's profile
    await page.goto("/#/profile/sample");

    // Then I see logout button, profile, and timeline of sample's posts
    await expect(
      page.locator("#logout-container [data-logout-button]")
    ).toBeVisible();
    await expect(
      page.locator("#profile-container header a[data-username]")
    ).toBeVisible();
    await expect(page.locator("#timeline-container")).toBeVisible();
    // And bloom form is not attached
    await expect(page.locator("#bloom-form-container form")).not.toBeAttached();
  });

  test("allows a user to unfollow a profile after following it", async ({page}) => {
    await loginAsJustSomeGuy(page);
    await page.goto("/#/profile/sample");

    const followButton = page.locator("#profile-container [data-action='follow']");
    await expect(followButton).toBeVisible();
    await expect(followButton).toHaveText("Follow");

    await followButton.click();
    await expect(followButton).toHaveText("Unfollow");

    await followButton.click();
    await expect(followButton).toHaveText("Follow");
  });
});
