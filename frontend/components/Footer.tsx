export function Footer() {
  return (
    <footer className="mt-32 border-t border-[#1F1F1F] py-12">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 text-sm text-[#8A8A8A] md:flex-row md:items-center md:justify-between">
        <p>CivicOs — Apache 2.0</p>
        <div className="flex items-center gap-6">
          <a
            href="https://github.com/sitara2007/CivicOs"
            target="_blank"
            rel="noreferrer"
            className="hover:text-[#EDEDED]"
          >
            GitHub
          </a>
          <a
            href="https://www.linkedin.com"
            target="_blank"
            rel="noreferrer"
            className="hover:text-[#EDEDED]"
          >
            LinkedIn
          </a>
          <a href="mailto:hello@civicos.ai" className="hover:text-[#EDEDED]">
            Email
          </a>
        </div>
      </div>
    </footer>
  );
}
