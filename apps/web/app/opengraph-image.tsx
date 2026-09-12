import { ImageResponse } from "next/og";

export const alt = "Copperas Cove Votes — Local ballot information, with sources you can check. Coverage is still being built.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return new ImageResponse(
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column",
      justifyContent: "center", background: "#faf9f5", color: "#292d29", padding: "80px",
      borderLeft: "18px solid #a28643" }}>
      <div style={{ fontSize: 28, color: "#315c49", marginBottom: 28 }}>COPPERAS COVE VOTES</div>
      <div style={{ fontSize: 76, fontWeight: 700, marginBottom: 24 }}>What’s on your ballot?</div>
      <div style={{ fontSize: 32 }}>Local information, with sources you can check.</div>
      <div style={{ fontSize: 24, marginTop: 36 }}>An independent project by Xavier Wells. Coverage is still being built.</div>
      <div style={{ fontSize: 24, marginTop: 28, color: "#315c49" }}>copperascovevotes.org</div>
    </div>, size,
  );
}
