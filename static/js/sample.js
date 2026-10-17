// Draws a high-contrast nutrition label on an off-screen canvas and returns a Blob.
export function generateSampleLabel() {
  const canvas = document.createElement("canvas");
  canvas.width = 1000;
  canvas.height = 1300;
  const ctx = canvas.getContext("2d");

  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = "#000";
  ctx.lineWidth = 8;
  ctx.strokeRect(30, 30, 940, 1240);

  ctx.fillStyle = "#000";
  ctx.font = "bold 70px Arial, sans-serif";
  ctx.fillText("Nutrition Facts", 70, 125);
  ctx.font = "38px Arial, sans-serif";
  ctx.fillText("Typical values per 100 g", 70, 185);

  const rows = [
    ["Energy (kcal) : 520", true],
    ["Total Fat (g) : 28.0", true],
    ["Saturated Fat (g) : 11.0", false],
    ["Carbohydrate (g) : 58.0", true],
    ["Total Sugars (g) : 24.0", false],
    ["Protein (g) : 6.8", true],
    ["Sodium (mg) : 640", true],
  ];
  let y = 270;
  rows.forEach(([text, bold]) => {
    ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(60, y - 52); ctx.lineTo(940, y - 52); ctx.stroke();
    ctx.font = (bold ? "bold " : "") + "50px Arial, sans-serif";
    ctx.fillText((bold ? "" : "    ") + text, 70, y);
    y += 85;
  });

  y += 40;
  ctx.font = "bold 40px Arial, sans-serif";
  ctx.fillText("Ingredients:", 70, y);
  ctx.font = "36px Arial, sans-serif";
  const ingredients = "Potato, Palm Oil, Sugar, Maltodextrin, Salt, Acidity Regulator (INS 330), " +
    "Flavour Enhancer (INS 621), Colour (INS 150d), Preservative (Sodium Benzoate).";
  const words = ingredients.split(" ");
  let line = "";
  y += 55;
  words.forEach(w => {
    const test = line ? line + " " + w : w;
    if (ctx.measureText(test).width > 860) { ctx.fillText(line, 70, y); y += 48; line = w; }
    else line = test;
  });
  if (line) ctx.fillText(line, 70, y);

  return new Promise((resolve, reject) => {
    canvas.toBlob(b => (b ? resolve(b) : reject(new Error("Canvas export failed."))), "image/png");
  });
}
