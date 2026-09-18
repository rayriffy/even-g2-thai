// Exercise the real parser and final writer gate without a device connection.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { parseFirmwareInput } from "../third_party/evenRealities-webflasher/src/lib/firmware.js";
import {
  assertPinnedTempleFlashCandidate,
  PogoFlashSafetyError,
} from "../third_party/evenRealities-webflasher/src/lib/pogoFlashBridge.js";

for (const [path, channel] of [
  ["../build/g2_2.3.0.24_thai.bin", "custom"],
  ["../.cache/g2_2.3.0.24.bin", "official"],
]) {
  const bytes = new Uint8Array(await readFile(new URL(path, import.meta.url)));
  const firmware = await parseFirmwareInput(bytes, path.split("/").pop());
  assert.equal(firmware.g2Version, "2.3.0.24");
  assert.equal(firmware.provenance.channel, channel);
  assert.equal(firmware.templeFlashEligible, true);
  assert.equal(firmware.templeFlashTarget.localOnly, true);
  assert.equal(firmware.templeFlashTarget.hardwareValidated, false);
  assert.equal(firmware.components.length, 6);
  if (channel === "custom") assert.equal(firmware.caseRecoveryEligible, false);
  await assertPinnedTempleFlashCandidate(firmware);

  // A forged parser digest must not hide a changed main payload.
  firmware.mainComponent.payload[128] ^= 1;
  await assert.rejects(assertPinnedTempleFlashCandidate(firmware), PogoFlashSafetyError);
  firmware.mainComponent.payload[128] ^= 1;
  await assertPinnedTempleFlashCandidate(firmware);

  // Correct payload with an unknown bundle pin still fails closed.
  firmware.fileSha256 = "0".repeat(64);
  await assert.rejects(assertPinnedTempleFlashCandidate(firmware), PogoFlashSafetyError);
  console.log(`Verified parser, writer pin and tamper rejection: ${path}`);
}
console.log("WEBFLASHER_ARTIFACTS_OK");
