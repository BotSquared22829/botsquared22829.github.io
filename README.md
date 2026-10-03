# BotSquared — FTC Team 22829

Scroll-driven landing page using the supplied team photos and branding. Plain HTML, CSS, and JavaScript; no package installation required.

Run `npm run dev` and open http://127.0.0.1:5173. Run `npm run check` for JavaScript syntax checks.

The page also works by opening `index.html` directly. It features a pinned robot-video scene, a three-chapter robot-building story, progressive text reveals, photo parallax, and a glass navigation bar with reading progress. Scrolling remains native; animation frames run only while scrolling or settling.

The mobile navigation and chapter controls support keyboards. Reduced motion and no JavaScript present the full story in a linear layout. Short screens keep the opening video pinned and show the robot chapters in a linear layout. Reduced-motion preferences can be changed while the page is open.

The opening scene uses `assets/robot-motion-black.mp4`, a pure-black robot render with an opening-frame poster. Home-page loads begin at the top of the story; section links and back/forward cache navigation retain their destination. Every frame is a keyframe and the MP4 metadata is at the beginning of the file for scroll seeking and progressive loading. It slides into the viewport at full size without scaling, then stays fixed while scrolling seeks through the video in either direction. Once playback finishes, scrolling continues into the team section. The video scales to the browser width at its original 16:9 proportions and stays vertically centered; very wide, short windows can crop the top and bottom. The pinned stage tracks the current viewport height. Reduced motion and no JavaScript retain native video controls. The preview server supports MP4 byte-range requests for seeking.

The initial left-to-right movement receives 1.7 times the scroll distance per video second. The pinned scene is longer so the later turn keeps roughly its previous pace; the entrance distance stays the same across screen sizes.

Team, outreach, sponsor, and contact details are based on the supplied website source. Review these before publishing.

## GitHub Pages

The organization site repository is `BotSquared22829/botsquared22829.github.io` and its address is https://botsquared22829.github.io/.

The `Publish website` workflow checks and builds each push to `main`, then publishes when the repository is public and Pages is configured to use GitHub Actions. `npm run build` produces `_site/` containing only the landing page and its referenced assets. Content-based CSS and JavaScript URL versions prevent browsers from reusing stale code after updates. Local server code and robot rendering scripts are excluded from the published website.

GitHub Free requires a public repository for Pages. In repository Settings → Pages, select **GitHub Actions** as the source. The workflow can also be run manually from the Actions tab.
