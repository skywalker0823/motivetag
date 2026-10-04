// Personal cards (api/v1/profile.py): colours and a cover photo, shown on my profile,
// in the settings preview and on other members' cards. The look is CSS variables on
// the card's element (static/css/member.css, "Personal cards").

const VARIABLES = {
  accent: "--card-accent",
  cover_from: "--cover-from",
  cover_to: "--cover-to",
  name_color: "--name-color",
};

/** Dresses `container` (which holds a .card-cover) in `card`; null restores the default. */
export function applyCard(container, card) {
  for (const [name, variable] of Object.entries(VARIABLES)) {
    if (card?.[name]) container.style.setProperty(variable, card[name]);
    else container.style.removeProperty(variable);
  }
  const cover = container.querySelector(".card-cover");
  if (cover) cover.style.backgroundImage = card?.cover ? `url("${card.cover}")` : "";
  container.classList.toggle("has-card-photo", Boolean(card?.cover));
}
