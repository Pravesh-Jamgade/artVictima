#include "pagetable_buffer.h"
#include "stats.h"
#include "config.hpp"
#include "log.h"
#include <iterator>

namespace ParametricDramDirectoryMSI
{

PageTableBuffer::PageTableBuffer(String name, core_id_t core_id, UInt32 size, UInt32 associativity, ComponentLatency access_latency, Mode mode)
   : m_size(size)
   , m_associativity(associativity)
   , m_access_latency(access_latency)
   , m_mode(mode)
   , m_access(0)
   , m_hit(0)
   , m_miss(0)
{
   LOG_ASSERT_ERROR(m_associativity > 0, "PageTableBuffer associativity must be greater than zero");
   LOG_ASSERT_ERROR(m_size > 0, "PageTableBuffer size must be greater than zero");

   m_num_sets = m_size / m_associativity;
   LOG_ASSERT_ERROR(m_num_sets > 0, "PageTableBuffer number of sets must be greater than zero");

   m_sets.resize(m_num_sets);

   registerStatsMetric(name, core_id, "access", &m_access);
   registerStatsMetric(name, core_id, "hit", &m_hit);
   registerStatsMetric(name, core_id, "miss", &m_miss);
}

PageTableBuffer::Key PageTableBuffer::makeKey(const std::vector<uint64_t> &vpn_indices) const
{
   Key key{};
   key.num_parts = (m_mode == Mode::LEAF_PT) ? 3 : 2;
   for (size_t i = 0; i < key.num_parts; ++i)
   {
      key.parts[i] = vpn_indices[i];
   }
   return key;
}

size_t PageTableBuffer::getSetIndex(const Key &key) const
{
   KeyHash hasher;
   return hasher(key) % m_num_sets;
}

PageTableBuffer::LookupResult PageTableBuffer::lookup(const std::vector<uint64_t> &vpn_indices, bool count)
{
   LookupResult result{false, 0, m_access_latency.getLatency()};

   Key key = makeKey(vpn_indices);
   size_t set_index = getSetIndex(key);

   auto dir_it = m_directory.find(key);
   if (count)
      m_access++;

   if (dir_it != m_directory.end())
   {
      auto &set = m_sets[dir_it->second.set_index];
      set.splice(set.begin(), set, dir_it->second.it);
      result.hit = true;
      result.base_address = dir_it->second.it->second;
      if (count)
         m_hit++;
      return result;
   }

   if (count)
      m_miss++;

   // Keep the computed set_index to maintain consistent eviction policy on insert
   (void)set_index;
   return result;
}

void PageTableBuffer::insert(const std::vector<uint64_t> &vpn_indices, IntPtr base_address)
{
   Key key = makeKey(vpn_indices);
   size_t set_index = getSetIndex(key);
   auto &set = m_sets[set_index];

   auto dir_it = m_directory.find(key);
   if (dir_it != m_directory.end())
   {
      dir_it->second.it->second = base_address;
      set.splice(set.begin(), set, dir_it->second.it);
      return;
   }

   if (set.size() >= m_associativity)
   {
      auto evict_it = std::prev(set.end());
      m_directory.erase(evict_it->first);
      set.pop_back();
   }

   set.push_front(std::make_pair(key, base_address));
   m_directory[key] = {set_index, set.begin()};
}

}
