"""A extension that adds party funds utilities"""
import sqlite3
from discord.ext import commands
from utils.config_reader import YAMLConfigReader
from utils.logger import Logger

class PartyFunds(commands.Cog):
    """Extension class"""
    def __init__(self, bot):
        self.bot = bot
        self.config = YAMLConfigReader()

    def get_party_fund_value(self, guild):
        conn = sqlite3.connect(self.config.data.database)
        try:
            cur = conn.cursor()
            cur.execute("SELECT Amount FROM party_fund WHERE ID IS " \
                        "(SELECT PartyFundID FROM server WHERE ID IS ?)",
                        (guild.id, ))
            result = cur.fetchone()
        finally:
            conn.close()
        return result[0] if len(result) > 0 else None

    def set_party_fund_value(self, guild, value):
        conn = sqlite3.connect(self.config.data.database)
        try:
            cur = conn.cursor()
            cur.execute("UPDATE party_fund SET Amount = ? WHERE ID IS " \
                        "(SELECT PartyFundID FROM server WHERE ID IS ?)",
                        (value, guild.id))
            conn.commit()
        finally:
            conn.close()

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        conn = sqlite3.connect(self.config.data.database)
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO party_fund VALUES (NULL, 0)")
            party_fund_row_id = cur.lastrowid
            cur.execute("SELECT COUNT(*) FROM server WHERE ID IS ?",
                        (guild.id, ))
            result = cur.fetchone()
            if result and result[0] == 0:
                cur.execute("INSERT INTO server VALUES (?, ?)",
                            (guild.id, party_fund_row_id))
            else:
                cur.execute("UPDATE server SET PartyFundID = ? WHERE ID IS ?",
                            (party_fund_row_id, guild.id))
            conn.commit()
            await Logger.log("Successfully added party fund for new server")
        finally:
            conn.close()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        conn = sqlite3.connect(self.config.data.database)
        try:
            cur = conn.cursor()
            cur.execute("SELECT PartyFundID FROM server WHERE ID IS ?",
                        (guild.id, ))
            result = cur.fetchone()
            if len(result) > 0:
                cur.execute("UPDATE server SET PartyFundID = ? WHERE ID IS ?",
                            (None, guild.id))
                cur.execute("DELETE FROM party_fund WHERE ID IS ?",
                            (result[0], ))
                conn.commit()
            await Logger.log("Removed party fund for leaving server")
        finally:
            conn.close()

    @commands.group(pass_context=True, help="Manage party funds")
    async def funds(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid subcommand')

    @funds.command()
    async def add(self, ctx, amount: float):
        current_value = self.get_party_fund_value(ctx.guild)
        if current_value is None:
            await ctx.send('Failed to add party funds')
            return
        new_total = amount + current_value
        self.set_party_fund_value(ctx.guild, new_total)
        await ctx.send(f'Party funds increased by {amount} GP(s). ' \
                       f'Now at {new_total} GP(s)')

    @funds.command()
    async def get(self, ctx):
        current_value = self.get_party_fund_value(ctx.guild)
        if current_value is None:
            await ctx.send('Failed to get party funds')
            return
        await ctx.send(f'Party fund contains {current_value} GP(s)')

    @funds.command()
    async def spend(self, ctx, amount: float):
        current_value = self.get_party_fund_value(ctx.guild)
        if current_value is None:
            await ctx.send('Failed to spend party funds')
            return
        new_total = current_value - amount
        self.set_party_fund_value(ctx.guild, new_total)
        await ctx.send(f'{amount} GP(s) of party fund spent. ' \
                       f'Now at {new_total} GP(s)')

def setup(bot):
    """Add the extension as a cog"""
    bot.add_cog(PartyFunds(bot))
