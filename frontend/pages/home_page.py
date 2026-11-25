import streamlit as st
from frontend.components.senator_card import avatar


def _go(page):
    st.session_state.page = page
    st.rerun()


def render(service):
    profile_count = len(service.senators)
    featured_senator = service.senators[0]
    with st.container(key="home_page"):
        with st.container(key="home_hero"):
            st.html(
                '<section class="home-hero home-shell">'
                '<div class="hero-spark hero-spark-left"></div><div class="hero-spark hero-spark-right"></div>'
                '<div class="eyebrow"><i></i><i></i><i></i><span>AI-powered Philippine civic education</span></div>'
                '<h1>Kilalanin ang<br><span>Senador Mo.</span></h1>'
                '<h2>Understand the people behind the policies.</h2>'
                '<p>Meet the members of the Philippine Senate, explore their legislative records, and understand documented positions through AI-powered conversations and objective comparisons.</p>'
                '</section>'
            )
            with st.container(key="home_hero_actions"):
                chat, compare = st.columns(2, gap="small")
                with chat:
                    if st.button("Talk with SEN’TO →", key="home_hero_chat", type="primary", use_container_width=True):
                        _go("CHAT")
                with compare:
                    if st.button("Compare Senators", key="home_hero_compare", use_container_width=True):
                        _go("COMPARE")
            st.html('<p class="hero-support">Explore public records. Discover verified sources. Stay informed.</p><p class="home-hero-bottom">CIVIC CURIOSITY STARTS HERE</p>')
        st.html(
            '<section class="home-feature-intro home-shell"><div><span class="section-kicker">PUBLIC RECORDS. HUMAN UNDERSTANDING.</span>'
            '<h2>Meet SEN’TO</h2><p>SEN’TO is an AI-powered civic education platform designed to make information about the Philippine Senate more accessible, understandable, and verifiable.</p>'
            '<a class="home-text-link" href="?view=chat">Start a conversation <b>→</b></a></div>'
            f'<div class="home-chat-preview"><div class="preview-heading">{avatar(featured_senator)}<div class="preview-person"><strong>{featured_senator["name"]}</strong><small>Public record assistant · 20th Congress</small></div><span>AI ASSISTANT</span></div>'
            '<div class="preview-user">How can I review a senator’s legislative record?</div>'
            '<div class="preview-answer"><small>SEN’TO / AI-GENERATED EXPLANATION</small><h3>Look beyond a bill’s title.</h3><p>A useful review separates what a senator filed, what they sponsored, and what became law. These are different parts of the legislative process.</p><a>Legislative process · undated</a></div>'
            '<div class="preview-note">Record not yet confirmed · No specific bill, vote, or committee role is confirmed.</div></div></section>'
            '<section class="home-explore home-shell"><span class="section-kicker">EXPLORE SEN’TO</span><h2>Two ways to get closer to the facts.</h2></section>'
        )
        st.html(
            f'<section class="home-actions home-shell" aria-label="Explore SEN’TO">'
            f'<article class="home-action-card"><span class="section-kicker">01 / TALK ABOUT SENATORS</span>'
            '<h3>Ask. Explore.<br>Understand.</h3>'
            '<p>Select a senator and explore available public records through a question-led conversation.</p>'
            '<a class="card-link" href="?view=chat">Explore Chat →</a>'
            f'<div class="card-portrait-row">{avatar(featured_senator)}<span>Choose a senator and ask a question</span></div></article>'
            '<article class="home-action-card compare-card"><span class="section-kicker">02 / COMPARE SENATORS</span>'
            '<h3>See the records<br>side by side.</h3>'
            '<p>Review the same public-record categories across two or three selected profiles.</p>'
            '<a class="card-link" href="?view=compare">Explore Compare →</a>'
            '<div class="comparison-preview"><span>Senator A</span><i></i><span>Senator B</span><i></i><span>Senator C</span></div></article>'
            '</section>'
        )
        st.html(
            '<section class="home-how"><span class="section-kicker">HOW SEN’TO WORKS</span><h2>A little curiosity goes a long way.</h2>'
            '<div class="steps"><article><b>01</b><h3>Choose a senator</h3><p>Browse the local reference directory and select a profile.</p></article>'
            '<article><b>02</b><h3>Ask or compare</h3><p>Explore a question or review selected records side by side.</p></article>'
            '<article><b>03</b><h3>Check the source</h3><p>Open available citations and keep coverage limits in view.</p></article></div></section>'
            '<section class="home-values"><span class="section-kicker">INFORMATION, NOT INFLUENCE</span><h2>Built for informed citizens.</h2>'
            '<div class="value-grid"><article><b>01</b><h3>Source-backed information</h3><p>Follow the supporting record when one is available.</p></article>'
            '<article><b>02</b><h3>Accessible explanations</h3><p>Make complex public records easier to explore.</p></article>'
            '<article><b>03</b><h3>Objective comparisons</h3><p>No rankings or endorsements. Review the records.</p></article></div>'
            '</section>'
        )
        with st.container(key="home_cta_panel"):
            st.html('<section class="home-cta"><span class="section-kicker">CIVIC CURIOSITY STARTS HERE</span><h2>Know more. Understand better.</h2><p>Start exploring the Philippine Senate with SEN’TO.</p></section>')
            with st.container(key="home_cta_actions"):
                left, right = st.columns(2, gap="small")
                with left:
                    if st.button("Talk with SEN’TO →", key="home_cta_chat", type="primary", use_container_width=True):
                        _go("CHAT")
                with right:
                    if st.button("Compare Senators", key="home_cta_compare", use_container_width=True):
                        _go("COMPARE")
        st.html(
            f'<footer class="home-footer"><div><b class="mini-brand">SEN<span class="gold">’</span><span class="red">TO</span></b><p>Kilalanin ang Senador Mo!</p></div><div class="footer-note">{profile_count} roster names · official Senate source dated 28 Jul 2025 · profile data may be incomplete.</div><p class="footer-disclaimer">SEN’TO is an independent civic education project and is not an official Philippine Senate service.</p></footer>'
        )
