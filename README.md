# BotSquared — FTC Team 22829

Scroll-driven landing page using the supplied team photos and branding. Plain HTML, CSS, and JavaScript; no package installation required.

Run `npm run dev` and open http://127.0.0.1:5173. Run `npm run check` for JavaScript syntax checks.

The page also works by opening `index.html` directly. It features a pinned robot-video scene, a three-chapter robot-building story, progressive text reveals, photo parallax, and a glass navigation bar with reading progress. Scrolling remains native; animation frames run only while scrolling or settling.

The navigation and chapter controls support keyboards. Reduced motion and no JavaScript present the full story in a linear layout. Short screens keep the opening video pinned and show the robot chapters in a linear layout. Reduced-motion preferences can be changed while the page is open. The About navigation link and the delayed “Learn More →” video button open `about.html`, a team introduction with a three-ball thinking animation. It is a visual demo with no AI processing; reduced motion shows the notice and full introduction immediately.

The opening scene uses `assets/robot-motion-black-right.mp4`, a pure-black robot render with an opening-frame poster. Home-page loads begin at the top of the story; section links and back/forward cache navigation retain their destination. Every frame is a keyframe and the MP4 metadata is at the beginning of the file for scroll seeking and progressive loading. It slides into the viewport at a consistent size, then stays fixed while scrolling seeks through the video in either direction. Once playback finishes, scrolling continues into the team section. The video keeps its original 16:9 proportions and stays centered, using up to 90% of the viewport width or stage height. Its width is capped at the native 1280 pixels to avoid upscaling and cropping. The pinned stage tracks the current viewport height. Reduced motion and no JavaScript retain native video controls. The preview server supports MP4 byte-range requests for seeking.

The initial left-to-right movement receives 1.7 times the scroll distance per video second. The pinned scene is longer so the later turn keeps roughly its previous pace; the entrance distance stays the same across screen sizes.

The About animation introduces the dots, reveals “Thinking” for one 2.2-second cycle, then shrinks into the upper left with “Innovating”. After another cycle, the dots and label fade out, leaving an info notice: “No AI was used; only visual effect”. The centered introduction stays pinned during its story. Its headline and first paragraph reveal automatically in a diagonal wave after the opening sequence. Scrolling brings in subsequent paragraphs as whole-block fades in the same position. Copy is local to `about.html`, with timing and scroll logic in `about.js`. Reduced motion and no JavaScript show the full copy in a readable linear layout.

Team, outreach, sponsor, and contact details are based on the supplied website source. Review these before publishing.

The gallery’s “Meet the Team →” button and the Team navigation link open `team.html`. The supplied group photo leads the page, beside five department cards that fill its height. Each plus button expands a panel across the photo-and-cards area, showing the department’s members in the photo area while every department title and control stays in its original position. The same button or Escape closes it; pressing the button during closing reopens from its current size. Another department’s plus switches the members. The group photo stays rendered beneath the solid expanded surface, so closing reveals it continuously. Spotlight controls are disabled placeholders for a later feature. The roster uses the names, roles, and portraits from the original supplied website; members without portraits use initials. The cards stack below the photo on smaller screens, and JavaScript-free viewing retains the descriptions and full roster without inactive controls.

## GitHub Pages

The organization site repository is `BotSquared22829/botsquared22829.github.io` and its address is https://botsquared22829.github.io/.

The `Publish website` workflow checks and builds each push to `main`, then publishes when the repository is public and Pages is configured to use GitHub Actions. `npm run build` produces `_site/` containing the landing page, About page, Team page, and their referenced assets. Content-based CSS and JavaScript URL versions prevent browsers from reusing stale code after updates. Local server code and robot rendering scripts are excluded from the published website.

GitHub Free requires a public repository for Pages. In repository Settings → Pages, select **GitHub Actions** as the source. The workflow can also be run manually from the Actions tab.
