// The scrambled-character field behind the thesis card (Aceternity's
// Evervault pattern); regenerated on every pointer move.

const CHARACTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

export function generateRandomString(length: number): string {
  let result = "";
  for (let i = 0; i < length; i++) result += CHARACTERS.charAt(Math.floor(Math.random() * CHARACTERS.length));
  return result;
}
