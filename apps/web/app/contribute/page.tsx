import type { Metadata } from "next";
import styles from "../home.module.css";

const description = "What to include when sharing local election information with the Copperas Cove project, and how submissions are checked before publication.";
export const metadata: Metadata = {
  title: "Contribute or report a mistake — What's on My Ballot?",
  description,
  openGraph: { title: "Help with Copperas Cove ballot information", description,
    images: [{ url: "/opengraph-image", width: 1200, height: 630, alt: "Copperas Cove Votes — Coverage is still being built." }] },
  twitter: { card: "summary_large_image", title: "Help with Copperas Cove ballot information", description,
    images: ["/twitter-image"] },
};

export default function Contribute() {
  return <main className={styles.home}><article className={styles.guidance}>
    <a href="/">Back to the ballot project</a>
    <h1>Have information to share, or spotted a mistake?</h1>
    <p>Local election information isn&apos;t always online. A handout from a public meeting,
      an official notice, or notes from speaking with a candidate can help fill a gap.</p>
    <h2>How to send it</h2>
    <p>Email <a href="mailto:info@copperascovevotes.org">info@copperascovevotes.org</a> with
      information or questions. Xavier reads these messages. Public uploads aren&apos;t open yet;
      this link opens your email app, not an upload form.</p>
    <p>Email is different from the ballot lookup: your message, sender address and any attachments
      are retained in the project mailbox. They aren&apos;t automatically added to the ballot
      database or published. Only send information you are comfortable sharing for review.</p>
    <h2>What to include</h2>
    <ul>
      <li>The election, office or candidate the information concerns, and the city or county.</li>
      <li>Where and when you got it: a public meeting, an election office, or a conversation.
        Identify the organization or the speaker&apos;s public role where relevant.</li>
      <li>A source link, document title and page number, or a clear copy of a public handout
        you are allowed to share. Include enough context to check the statement.</li>
      <li>Keep exact quotes separate from your notes or interpretation. Say when something
        is only your recollection. Don&apos;t upload a private conversation or recording
        without the permission needed to share it.</li>
    </ul>
    <p>Leave out voter addresses, registration details, signatures, private contact details,
      and other people&apos;s personal information. Never send passwords or identity documents.</p>
    <h2>Reporting a mistake</h2>
    <p>Email <a href="mailto:corrections@copperascovevotes.org">corrections@copperascovevotes.org</a>.
      It reaches the same project inbox.</p>
    <p>Include the page link, the wording you think is wrong, your proposed correction, and
      a source we can check. You don&apos;t need to share your home address or location.</p>
    <h2>What happens during review</h2>
    <ol>
      <li><strong>Submitted, not verified.</strong> Email arrives privately in the project inbox.
        Relevant material can then be entered as a private draft for review.
        Sending it won&apos;t put it on the public site.</li>
      <li><strong>Checked against evidence.</strong> A human compares basic official facts
        with their source. Interviews, candidate statements and interpretation need two
        human reviewers. Missing evidence or disagreements stay unresolved.</li>
      <li><strong>Published separately.</strong> Reviewed information still needs a publication
        decision. Candidate statements stay labeled as statements, not independent facts.
        Published information includes its source; corrections preserve the earlier history.</li>
    </ol>
    <p>Email is available now; public uploads and some review tools are still being built.
      These rules don&apos;t mean every submission can be reviewed or published immediately.</p>
  </article></main>;
}
